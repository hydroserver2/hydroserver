import uuid

from datetime import datetime
from typing import Literal, Optional, get_args
from django.db import transaction
from django.db.models.query import QuerySet
from django.utils import timezone
from django.contrib.auth import get_user_model

from core.types import Unset
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from processing.quality.models import QCHistory, QCSession, QCSessionDependency, SessionStatus
from interfaces.api.http.errors import BadRequestError, NotFoundError
from interfaces.api.service import APIService
from interfaces.api.services.sta import ObservationAPIService
from interfaces.api.services.quality.history import QCHistoryAPIService
from interfaces.api.schemas.quality.session import (
    QualityControlSessionOrderByFields,
    QualityControlSessionResponse,
)


User = get_user_model()

observation_service = ObservationAPIService()
qc_history_service = QCHistoryAPIService()


class QCSessionAPIService(APIService):

    order_by_fields = {
        "id",
        "created_at",
        "phenomenon_time_start",
        "phenomenon_time_end",
        "status",
        "committed_at",
    }

    @staticmethod
    def select_related_fields(queryset: QuerySet) -> QuerySet:
        return queryset.select_related("created_by").prefetch_related("dependencies")

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

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        action: Literal["view", "edit"] = "view",
    ) -> QCSession:
        history = qc_history_service.get_history_for_action(principal=principal, uid=history, action=action)

        if isinstance(session, uuid.UUID):
            try:
                session = self.select_related_fields(
                    QCSession.objects.filter(history=history)
                ).get(pk=session)
            except QCSession.DoesNotExist:
                raise NotFoundError(f"QC session with ID {str(session)} does not exist.")
        elif session.history_id != history.pk:
            raise NotFoundError(f"QC session with ID {str(session.id)} does not exist.")

        return session

    def get_item(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
    ):
        session = self.get(principal=principal, history=history, session=session, action="view")

        return {
            "data": QualityControlSessionResponse.model_validate(session),
            "included": {},
        }

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        history: uuid.UUID | QCHistory,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
    ):
        filtering = filtering or {}
        history = qc_history_service.get_history_for_action(principal=principal, uid=history, action="view")
        ancestor_of = filtering.get("ancestor_of")

        if ancestor_of:
            try:
                target = QCSession.objects.get(pk=ancestor_of, history=history)
            except QCSession.DoesNotExist:
                raise NotFoundError(f"QC session with ID {str(ancestor_of)} does not exist.")

            session_ids = self._get_ancestor_ids({target.pk})
            queryset = QCSession.objects.filter(history=history, pk__in=session_ids)
        else:
            queryset = QCSession.objects.filter(history=history)

            if filtering.get("status"):
                queryset = queryset.filter(status=filtering["status"])

            if filtering.get("range_start"):
                queryset = queryset.filter(phenomenon_time_end__gt=filtering["range_start"])

            if filtering.get("range_end"):
                queryset = queryset.filter(phenomenon_time_start__lt=filtering["range_end"])

            if filtering.get("include_ancestors"):
                session_ids = set(queryset.values_list("pk", flat=True))
                session_ids |= self._get_ancestor_ids(session_ids)
                queryset = QCSession.objects.filter(history=history, pk__in=session_ids)

        order_by = order_by or []
        if order_by:
            queryset = self.apply_ordering(
                queryset, order_by, list(get_args(QualityControlSessionOrderByFields))
            )
        else:
            queryset = queryset.order_by("phenomenon_time_start")

        queryset = self.select_related_fields(queryset)
        queryset, meta = self.apply_pagination(queryset, offset, limit)
        sessions = list(queryset.all())

        return {
            "data": [QualityControlSessionResponse.model_validate(s) for s in sessions],
            "meta": meta,
            "included": {},
        }

    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        history: uuid.UUID | QCHistory,
        phenomenon_time_start: datetime,
        phenomenon_time_end: datetime,
        description: str | None = None,
        uid: uuid.UUID | Unset = Unset,
    ):
        history = qc_history_service.get_history_for_action(principal=principal, uid=history, action="edit")
        source_datastream = history.source_datastream
        if source_datastream is None:
            raise BadRequestError("This history has no source datastream.")

        source_checksum = observation_service.get_checksum(
            datastream=source_datastream,
            phenomenon_time_start=phenomenon_time_start,
            phenomenon_time_end=phenomenon_time_end,
        )

        session = QCSession(
            pk=uid if uid is not Unset else uuid.uuid7(),
            history=history,
            created_by=principal if isinstance(principal, User) else None,
            phenomenon_time_start=phenomenon_time_start,
            phenomenon_time_end=phenomenon_time_end,
            description=description,
            source_checksum=source_checksum,
        )
        session.full_clean()
        session.save()

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

        return {"id": session.pk}

    @transaction.atomic
    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
        description: str | None | Unset = Unset,
    ):
        session = self.get(principal=principal, history=history, session=session, action="edit")

        if description is not Unset:
            session.description = description

        session.full_clean()
        session.save()

    @transaction.atomic
    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
    ) -> None:
        session = self.get(principal=principal, history=history, session=session, action="edit")

        if session.status != SessionStatus.IN_PROGRESS:
            raise BadRequestError("Only in-progress sessions can be deleted.")

        session.delete()

    @transaction.atomic
    def commit(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        history: uuid.UUID | QCHistory,
        session: uuid.UUID | QCSession,
    ):
        history = qc_history_service.get_history_for_action(principal=principal, uid=history, action="edit")
        session = self.get(principal=principal, history=history, session=session, action="edit")

        managed_datastream = history.managed_datastream
        source_datastream = history.source_datastream

        session.managed_checksum = observation_service.get_checksum(
            datastream=managed_datastream,
            phenomenon_time_start=session.phenomenon_time_start,
            phenomenon_time_end=session.phenomenon_time_end,
        )
        session.status = SessionStatus.COMMITTED
        session.committed_at = timezone.now()
        session.full_clean()
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

        history.full_clean()
        history.save()
