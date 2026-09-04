import uuid
from typing import Literal

from pydantic import Field, ConfigDict, validate_call
from django.db import transaction
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model

from core.types import Unset
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import BadRequestError, PermissionDeniedError, NotFoundError
from interfaces.api.service import APIService
from core.sta.models import Datastream
from processing.quality.models import QCHistory


User = get_user_model()


class QCHistoryAPIService(APIService):

    order_by_fields = {
        "id",
        "created_at",
        "managed_datastream_id",
        "source_datastream_id",
        "phenomenon_time_start",
        "phenomenon_time_end",
    }

    @staticmethod
    def select_related_fields(queryset: QuerySet, expand_related: bool | None = None) -> QuerySet:
        if expand_related:
            return queryset.select_related(
                "managed_datastream__monitoring_site__workspace",
                "managed_datastream__method",
                "managed_datastream__observed_property",
                "managed_datastream__unit",
                "managed_datastream__processing_level",
                "source_datastream__monitoring_site__workspace",
                "source_datastream__method",
                "source_datastream__observed_property",
                "source_datastream__unit",
                "source_datastream__processing_level",
            ).prefetch_related(
                "managed_datastream__datastream_linked_resources",
                "source_datastream__datastream_linked_resources",
            )

        return queryset.select_related(
            "managed_datastream__monitoring_site__workspace",
            "source_datastream__monitoring_site__workspace",
        )

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        self,
        history: uuid.UUID | QCHistory,
        principal: User | ServiceAccount | AnonymousPrincipal | Unset = Unset,
        action: Literal["view", "edit", "delete"] = "view",
        expand_related: bool | None = None,
    ) -> QCHistory:
        """Get a QC history."""

        if isinstance(history, uuid.UUID):
            try:
                history = self.select_related_fields(
                    QCHistory.objects, expand_related=expand_related
                ).get(pk=history)
            except QCHistory.DoesNotExist:
                raise NotFoundError(f"QC history with ID {str(history)} does not exist.")

        if principal is not Unset:
            managed_datastream = principal.annotate_permissions(
                Datastream.objects.filter(pk=history.managed_datastream_id)
            ).get()

            if not principal.can_view(managed_datastream):
                raise NotFoundError(f"QC history with ID {str(history.id)} does not exist.")

            if action != "view" and not getattr(principal, f"can_{action}")(managed_datastream):
                raise PermissionDeniedError(f"You do not have permission to {action} this QC history.")

        return history

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] = Field(default_factory=list),
        expand_related: bool | None = None,
        managed_datastream_id: list[uuid.UUID] | Unset = Unset,
        source_datastream_id: list[uuid.UUID] | Unset = Unset,
    ) -> tuple[int, QuerySet[QCHistory]]:
        """Return a collection of QC histories."""

        queryset = QCHistory.objects

        if managed_datastream_id is not Unset:
            queryset = queryset.filter(managed_datastream_id__in=managed_datastream_id)

        if source_datastream_id is not Unset:
            queryset = queryset.filter(source_datastream_id__in=source_datastream_id)

        if not all(term.lstrip("-") in self.order_by_fields for term in order_by):
            raise BadRequestError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "-id")
        queryset = self.select_related_fields(queryset, expand_related=expand_related)
        queryset = queryset.filter(
            managed_datastream__in=principal.filter_by_permission(Datastream.objects, "can_view")
        ).distinct()

        count = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]

        return count, queryset

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        managed_datastream: uuid.UUID | Datastream,
        source_datastream: uuid.UUID | Datastream,
        uid: uuid.UUID = Field(default_factory=uuid.uuid7),
    ) -> QCHistory:
        """Create a QC history linking a managed datastream to its source datastream."""

        if isinstance(managed_datastream, uuid.UUID):
            try:
                managed_datastream = Datastream.objects.select_related(
                    "monitoring_site__workspace", "processing_level"
                ).get(pk=managed_datastream)
            except Datastream.DoesNotExist:
                raise NotFoundError("Managed datastream does not exist.")

        if isinstance(source_datastream, uuid.UUID):
            try:
                source_datastream = Datastream.objects.select_related(
                    "monitoring_site__workspace", "processing_level"
                ).get(pk=source_datastream)
            except Datastream.DoesNotExist:
                raise NotFoundError("Source datastream does not exist.")

        if not principal.can_edit(managed_datastream):
            raise PermissionDeniedError(
                "You do not have permission to create a QC history for this datastream."
            )

        history = QCHistory(
            pk=uid,
            managed_datastream=managed_datastream,
            source_datastream=source_datastream,
        )
        history.full_clean()
        history.save()

        return self.get(history=history.pk, principal=principal, expand_related=True)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def delete(
        self,
        history: uuid.UUID | QCHistory,
        principal: User | ServiceAccount | AnonymousPrincipal,
    ) -> None:
        """Delete a QC history and all associated sessions."""

        history = self.get(history=history, principal=principal, action="delete")
        history.delete()
