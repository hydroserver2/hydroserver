import uuid

from typing import Literal, Optional, get_args
from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model

from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import Datastream
from processing.quality.models import QCHistory
from interfaces.api.http.errors import ConflictError, PermissionDeniedError, NotFoundError
from interfaces.api.service import APIService
from interfaces.api.schemas.quality.history import (
    QualityControlHistoryOrderByFields,
    QualityControlHistoryResponse,
    QualityControlHistoryPostBody,
    QUALITY_CONTROL_HISTORY_INCLUDE_RELATIONS,
)


User = get_user_model()


class QCHistoryAPIService(APIService):
    INCLUDE_RELATIONS = QUALITY_CONTROL_HISTORY_INCLUDE_RELATIONS

    def get_history_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID | QCHistory,
        action: Literal["view", "edit", "delete"],
        select_related: Optional[list[str]] = None,
        prefetch_related: Optional[list[str]] = None,
    ) -> QCHistory:
        if isinstance(uid, QCHistory):
            history = uid
        else:
            queryset = QCHistory.objects.filter(pk=uid).select_related(
                "managed_datastream__monitoring_site__workspace",
                "source_datastream__monitoring_site__workspace",
            )
            if select_related:
                queryset = queryset.select_related(*select_related)
            if prefetch_related:
                queryset = queryset.prefetch_related(*prefetch_related)

            try:
                history = queryset.get()
            except QCHistory.DoesNotExist:
                raise NotFoundError(f"QC history with ID {uid} does not exist.")

        managed_datastream = principal.annotate_permissions(
            Datastream.objects.filter(pk=history.managed_datastream_id)
        ).get()

        if not principal.can_view(managed_datastream):
            raise NotFoundError(f"QC history with ID {uid} does not exist.")

        if action != "view" and not getattr(principal, f"can_{action}")(managed_datastream):
            raise PermissionDeniedError(f"You do not have permission to {action} this QC history.")

        return history

    @classmethod
    def _include_query_hints(
        cls, requested_includes: set[str]
    ) -> tuple[list[str], list[str]]:
        select_paths = [
            cls.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
        ]
        prefetch_paths = []

        if "managedDatastream" in requested_includes:
            prefetch_paths.append("managed_datastream__datastream_linked_resources")
        if "sourceDatastream" in requested_includes:
            prefetch_paths.append("source_datastream__datastream_linked_resources")

        return select_paths, prefetch_paths

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        queryset = QCHistory.objects

        for field in ["managed_datastream_id", "source_datastream_id"]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(QualityControlHistoryOrderByFields)),
            )
        else:
            queryset = queryset.order_by("-id")

        queryset = queryset.select_related(
            "managed_datastream__monitoring_site__workspace",
            "source_datastream__monitoring_site__workspace",
        )

        if requested_includes:
            select_paths, prefetch_paths = self._include_query_hints(requested_includes)
            queryset = queryset.select_related(*select_paths)
            if prefetch_paths:
                queryset = queryset.prefetch_related(*prefetch_paths)

        queryset = queryset.filter(
            managed_datastream__in=principal.filter_by_permission(Datastream.objects, "can_view")
        ).distinct()

        queryset, meta = self.apply_pagination(queryset, offset, limit)
        histories = list(queryset.all())

        return {
            "data": [QualityControlHistoryResponse.model_validate(h) for h in histories],
            "meta": meta,
            "included": self.resolve_includes(
                histories, requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        select_paths, prefetch_paths = self._include_query_hints(requested_includes)

        history = self.get_history_for_action(
            principal=principal,
            uid=uid,
            action="view",
            select_related=select_paths,
            prefetch_related=prefetch_paths,
        )

        return {
            "data": QualityControlHistoryResponse.model_validate(history),
            "included": self.resolve_includes(
                [history], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: QualityControlHistoryPostBody,
    ):
        try:
            managed_datastream = Datastream.objects.select_related(
                "monitoring_site__workspace"
            ).get(pk=data.managed_datastream_id)
        except Datastream.DoesNotExist:
            raise NotFoundError("Managed datastream does not exist.")

        try:
            source_datastream = Datastream.objects.select_related(
                "monitoring_site__workspace"
            ).get(pk=data.source_datastream_id)
        except Datastream.DoesNotExist:
            raise NotFoundError("Source datastream does not exist.")

        if not principal.can_edit(managed_datastream):
            raise PermissionDeniedError(
                "You do not have permission to create a QC history for this datastream."
            )

        history = QCHistory(
            managed_datastream=managed_datastream,
            source_datastream=source_datastream,
        )
        history.full_clean()

        try:
            history.save()
        except IntegrityError:
            raise ConflictError("The operation could not be completed due to a resource conflict.")

        return {"id": history.pk}

    @transaction.atomic
    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
    ):
        history = self.get_history_for_action(principal=principal, uid=uid, action="delete")
        history.delete()
