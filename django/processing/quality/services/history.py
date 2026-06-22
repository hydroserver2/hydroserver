import uuid
import uuid6
from typing import Literal

from pydantic import Field, ConfigDict, validate_call
from django.db import transaction
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model

from core.types import Unset
from core.iam.models import APIKey
from core.service import ServiceUtils
from core.sta.models import Datastream
from processing.quality.models import QCHistory


User = get_user_model()


class QCHistoryService(ServiceUtils):

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
                "managed_datastream__thing__workspace",
                "managed_datastream__sensor",
                "managed_datastream__observed_property",
                "managed_datastream__unit",
                "managed_datastream__processing_level",
                "source_datastream__thing__workspace",
                "source_datastream__sensor",
                "source_datastream__observed_property",
                "source_datastream__unit",
                "source_datastream__processing_level",
            ).prefetch_related(
                "managed_datastream__thing__locations",
                "managed_datastream__datastream_tags",
                "managed_datastream__datastream_file_attachments",
                "source_datastream__thing__locations",
                "source_datastream__datastream_tags",
                "source_datastream__datastream_file_attachments",
            )

        return queryset.select_related(
            "managed_datastream__thing__workspace",
            "source_datastream__thing__workspace",
        )

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        self,
        history: uuid.UUID | QCHistory,
        principal: User | APIKey | None | Unset = Unset,
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
                raise LookupError(f"QC history with ID {str(history)} does not exist.")

        if principal is not Unset:
            permissions = history.get_principal_permissions(principal=principal)

            if "view" not in permissions:
                raise LookupError(f"QC history with ID {str(history.id)} does not exist.")

            if action not in permissions:
                raise PermissionError(f"You do not have permission to {action} this QC history.")

        return history

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        principal: User | APIKey | None,
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
            raise ValueError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "-id")
        queryset = self.select_related_fields(queryset, expand_related=expand_related)
        queryset = queryset.visible(principal=principal).distinct()

        count = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]

        return count, queryset

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | APIKey | None,
        managed_datastream: uuid.UUID | Datastream,
        source_datastream: uuid.UUID | Datastream,
        uid: uuid.UUID = Field(default_factory=uuid6.uuid7),
    ) -> QCHistory:
        """Create a QC history linking a managed datastream to its source datastream."""

        if isinstance(managed_datastream, uuid.UUID):
            try:
                managed_datastream = Datastream.objects.select_related(
                    "thing__workspace", "processing_level"
                ).get(pk=managed_datastream)
            except Datastream.DoesNotExist:
                raise LookupError("Managed datastream does not exist.")

        if isinstance(source_datastream, uuid.UUID):
            try:
                source_datastream = Datastream.objects.select_related(
                    "thing__workspace", "processing_level"
                ).get(pk=source_datastream)
            except Datastream.DoesNotExist:
                raise LookupError("Source datastream does not exist.")

        if not QCHistory.can_principal_create(
            principal=principal, managed_datastream=managed_datastream
        ):
            raise PermissionError(
                "You do not have permission to create a QC history for this datastream."
            )

        if managed_datastream.thing.workspace_id != source_datastream.thing.workspace_id:
            raise ValueError(
                "The managed datastream and source datastream must belong to the same workspace."
            )

        if managed_datastream.processing_level_id == source_datastream.processing_level_id:
            raise ValueError(
                "The managed datastream must have a different processing level than the source datastream."
            )

        if QCHistory.objects.filter(managed_datastream=managed_datastream).exists():
            raise ValueError("The managed datastream already has a QC history.")

        history = QCHistory.objects.create(
            pk=uid,
            managed_datastream=managed_datastream,
            source_datastream=source_datastream,
        )

        return self.get(history=history.pk, principal=principal, expand_related=True)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def delete(
        self,
        history: uuid.UUID | QCHistory,
        principal: User | APIKey | None,
    ) -> None:
        """Delete a QC history and all associated sessions."""

        history = self.get(history=history, principal=principal, action="delete")
        history.delete()
