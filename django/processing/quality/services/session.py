import uuid
import uuid6
from datetime import datetime
from typing import Literal

from pydantic import Field, ConfigDict, validate_call
from django.db import transaction
from django.db.models.query import QuerySet
from django.utils import timezone
from django.contrib.auth import get_user_model

from core.types import Unset
from core.iam.models import APIKey
from core.service import ServiceUtils
from core.sta.services import ObservationService
from processing.quality.models import QCHistory, QCSession, QCSessionDependency, SessionStatus
from processing.quality.services.history import QCHistoryService


User = get_user_model()

observation_service = ObservationService()
qc_history_service = QCHistoryService()


class QCSessionService(ServiceUtils):

    order_by_fields = {
        "id",
        "created_at",
        "phenomenon_time_start",
        "phenomenon_time_end",
        "status",
        "committed_at",
    }

    @staticmethod
    def select_related_fields(queryset: QuerySet, expand_related: bool | None = None) -> QuerySet:
        queryset = queryset.select_related("created_by")

        if expand_related:
            queryset = queryset.prefetch_related("dependencies", "operations")

        return queryset

    @staticmethod
    def _get_ancestor_ids(session_ids: set[uuid.UUID]) -> set[uuid.UUID]:
        """Return the transitive closure of dependency IDs for the given session IDs."""

        ancestor_ids: set[uuid.UUID] = set()
        frontier = set(session_ids)

        while frontier:
            next_ids = set(
                QCSessionDependency.objects.filter(session_id__in=frontier)
                .exclude(dependency_id__in=ancestor_ids)
                .values_list("dependency_id", flat=True)
            )

            if not next_ids:
                break

            ancestor_ids |= next_ids
            frontier = next_ids

        return ancestor_ids

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        self,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        principal: User | APIKey | None | Unset = Unset,
        action: Literal["view", "edit"] = "view",
        expand_related: bool | None = None,
    ) -> QCSession:
        """Get a session belonging to a QC history."""

        history = qc_history_service.get(history=history, principal=principal, action=action)

        if isinstance(session, uuid.UUID):
            try:
                session = self.select_related_fields(
                    QCSession.objects.filter(history=history), expand_related=expand_related
                ).get(pk=session)
            except QCSession.DoesNotExist:
                raise LookupError(f"QC session with ID {str(session)} does not exist.")
        elif session.history_id != history.pk:
            raise LookupError(f"QC session with ID {str(session.id)} does not exist.")

        return session

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        history: uuid.UUID | QCHistory,
        principal: User | APIKey | None,
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] = Field(default_factory=list),
        expand_related: bool | None = None,
        status: Literal["in_progress", "committed"] | Unset = Unset,
        range_start: datetime | Unset = Unset,
        range_end: datetime | Unset = Unset,
        ancestor_of: uuid.UUID | Unset = Unset,
        include_ancestors: bool = False,
    ) -> tuple[int, QuerySet[QCSession]]:
        """Return a collection of sessions for a QC history."""

        history = qc_history_service.get(history=history, principal=principal, action="view")

        if not all(term.lstrip("-") in self.order_by_fields for term in order_by):
            raise ValueError(f"Invalid order_by field(s): {order_by}")

        if ancestor_of is not Unset:
            try:
                target = QCSession.objects.get(pk=ancestor_of, history=history)
            except QCSession.DoesNotExist:
                raise LookupError(f"QC session with ID {str(ancestor_of)} does not exist.")

            session_ids = self._get_ancestor_ids({target.pk})
            queryset = QCSession.objects.filter(history=history, pk__in=session_ids)
        else:
            queryset = QCSession.objects.filter(history=history)

            if status is not Unset:
                queryset = queryset.filter(status=status)

            if range_start is not Unset:
                queryset = queryset.filter(phenomenon_time_end__gt=range_start)

            if range_end is not Unset:
                queryset = queryset.filter(phenomenon_time_start__lt=range_end)

            if include_ancestors:
                session_ids = set(queryset.values_list("pk", flat=True))
                session_ids |= self._get_ancestor_ids(session_ids)
                queryset = QCSession.objects.filter(history=history, pk__in=session_ids)

        queryset = queryset.order_by(*order_by, "phenomenon_time_start")
        queryset = self.select_related_fields(queryset, expand_related=expand_related)

        count = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]

        return count, queryset

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | APIKey | None,
        history: uuid.UUID | QCHistory,
        phenomenon_time_start: datetime,
        phenomenon_time_end: datetime,
        description: str | None = None,
        uid: uuid.UUID = Field(default_factory=uuid6.uuid7),
    ) -> QCSession:
        """Create a new in-progress session for a QC history."""

        history = qc_history_service.get(history=history, principal=principal, action="edit")

        if phenomenon_time_end <= phenomenon_time_start:
            raise ValueError("phenomenon_time_end must be after phenomenon_time_start.")

        source_datastream = history.source_datastream
        if source_datastream is None:
            raise ValueError("This history has no source datastream.")

        if (
            source_datastream.phenomenon_end_time is not None
            and phenomenon_time_end > source_datastream.phenomenon_end_time
        ):
            raise ValueError(
                "phenomenon_time_end cannot extend past the source datastream's current end time."
            )

        if QCSession.objects.filter(history=history, status=SessionStatus.IN_PROGRESS).exists():
            raise ValueError("This history already has an in-progress session.")

        source_checksum = observation_service.get_checksum(
            datastream=source_datastream,
            phenomenon_time_start=phenomenon_time_start,
            phenomenon_time_end=phenomenon_time_end,
        )

        session = QCSession.objects.create(
            pk=uid,
            history=history,
            created_by=principal if isinstance(principal, User) else None,
            phenomenon_time_start=phenomenon_time_start,
            phenomenon_time_end=phenomenon_time_end,
            description=description,
            source_checksum=source_checksum,
        )

        dependency_ids = QCSession.objects.filter(
            history=history,
            status=SessionStatus.COMMITTED,
            phenomenon_time_start__lt=phenomenon_time_end,
            phenomenon_time_end__gt=phenomenon_time_start,
        ).values_list("pk", flat=True)

        QCSessionDependency.objects.bulk_create([
            QCSessionDependency(session=session, dependency_id=dependency_id)
            for dependency_id in dependency_ids
        ])

        return self.get(history=history, session=session.pk, principal=principal, expand_related=True)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        principal: User | APIKey | None,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        description: str | None | Unset = Unset,
    ) -> QCSession:
        """Update an in-progress session's description."""

        session = self.get(history=history, session=session, principal=principal, action="edit")

        if session.status != SessionStatus.IN_PROGRESS:
            raise ValueError("Only in-progress sessions can be updated.")

        if description is not Unset:
            session.description = description

        session.save()

        return self.get(history=session.history_id, session=session.pk, principal=principal, expand_related=True)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def delete(
        self,
        principal: User | APIKey | None,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
    ) -> None:
        """Delete an in-progress session."""

        session = self.get(history=history, session=session, principal=principal, action="edit")

        if session.status != SessionStatus.IN_PROGRESS:
            raise ValueError("Only in-progress sessions can be deleted.")

        session.delete()

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def commit(
        self,
        principal: User | APIKey | None,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
    ) -> QCSession:
        """Commit an in-progress session.

        Assumes the QC App has already pushed the session's edited observations to the
        managed datastream and verified checksums on the client side per Section 7.4.
        """

        history = qc_history_service.get(history=history, principal=principal, action="edit")
        session = self.get(history=history, session=session, principal=principal, action="edit")

        if session.status != SessionStatus.IN_PROGRESS:
            raise ValueError("Only in-progress sessions can be committed.")

        managed_datastream = history.managed_datastream
        source_datastream = history.source_datastream

        session.managed_checksum = observation_service.get_checksum(
            datastream=managed_datastream,
            phenomenon_time_start=session.phenomenon_time_start,
            phenomenon_time_end=session.phenomenon_time_end,
        )
        session.status = SessionStatus.COMMITTED
        session.committed_at = timezone.now()
        session.save()

        new_start = session.phenomenon_time_start
        new_end = session.phenomenon_time_end

        if history.phenomenon_time_start is not None:
            new_start = min(new_start, history.phenomenon_time_start)
        if history.phenomenon_time_end is not None:
            new_end = max(new_end, history.phenomenon_time_end)

        history.phenomenon_time_start = new_start
        history.phenomenon_time_end = new_end
        history.managed_checksum = observation_service.get_checksum(
            datastream=managed_datastream,
            phenomenon_time_start=new_start,
            phenomenon_time_end=new_end,
        )

        if source_datastream is not None:
            history.source_checksum = observation_service.get_checksum(
                datastream=source_datastream,
                phenomenon_time_start=new_start,
                phenomenon_time_end=new_end,
            )

        history.save()

        return self.get(history=history, session=session.pk, principal=principal, expand_related=True)
