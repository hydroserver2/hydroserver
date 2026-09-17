import uuid

from typing import Literal, Optional, get_args
from django.contrib.auth import get_user_model
from django.db import transaction

from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.types import Unset
from processing.products.models import DataProductTransformation, DataProductTransformationInput
from interfaces.api.http.errors import BadRequestError, NotFoundError, PermissionDeniedError
from interfaces.api.service import APIService
from interfaces.api.services.products.task import DataProductTaskAPIService
from interfaces.api.schemas.products.transformation import (
    DataProductTransformationFields,
    DataProductTransformationOrderByFields,
    DataProductTransformationPatchBody,
    DataProductTransformationPostBody,
    DataProductTransformationResponse,
    TransformationInputPostBody,
    DATA_PRODUCT_TRANSFORMATION_INCLUDE_RELATIONS,
)

User = get_user_model()
data_product_task_service = DataProductTaskAPIService()


class DataProductTransformationAPIService(APIService):
    INCLUDE_RELATIONS = DATA_PRODUCT_TRANSFORMATION_INCLUDE_RELATIONS

    @staticmethod
    def _include_query_hints(requested_includes: set[str]) -> tuple[list[str], list[str]]:
        select_paths = []
        prefetch_paths = []

        if "outputDatastream" in requested_includes:
            select_paths += ["output_datastream", "output_datastream__monitoring_site"]
            prefetch_paths.append("output_datastream__datastream_linked_resources")
        if "ratingCurve" in requested_includes:
            select_paths.append("rating_curve")
            prefetch_paths.append("rating_curve__points")

        return select_paths, prefetch_paths

    def get_transformation_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        select_related: Optional[list[str]] = None,
        prefetch_related: Optional[list[str]] = None,
    ) -> DataProductTransformation:
        queryset = DataProductTransformation.objects.filter(pk=uid)

        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)

        try:
            transformation = queryset.get()
        except DataProductTransformation.DoesNotExist:
            raise NotFoundError(f"DataProductTransformation with ID {uid} does not exist.")

        if not principal.can_view(transformation):
            raise NotFoundError(f"DataProductTransformation with ID {uid} does not exist.")

        if action != "view" and not getattr(principal, f"can_{action}")(transformation):
            raise PermissionDeniedError(
                f"You do not have permission to {action} this transformation."
            )

        return transformation

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
        filtering = filtering or {}
        queryset = DataProductTransformation.objects.all()

        for field in [
            "transformation_type",
            "output_datastream_id",
            "input_datastreams__datastream_id",
            "task_id",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if "workspace_id" in filtering:
            queryset = self.apply_filters(
                queryset, "task__monitoring_site__workspace_id", filtering["workspace_id"]
            )

        if order_by:
            queryset = self.apply_ordering(
                queryset, order_by, list(get_args(DataProductTransformationOrderByFields))
            )
        else:
            queryset = queryset.order_by("id")

        queryset = queryset.prefetch_related("input_datastreams")

        if requested_includes:
            select_paths, prefetch_paths = self._include_query_hints(requested_includes)
            queryset = queryset.select_related(*select_paths)
            if prefetch_paths:
                queryset = queryset.prefetch_related(*prefetch_paths)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()
        queryset, meta = self.apply_pagination(queryset, offset, limit)
        transformations = list(queryset.all())

        return {
            "data": [
                DataProductTransformationResponse.model_validate(t) for t in transformations
            ],
            "meta": meta,
            "included": self.resolve_includes(
                transformations, requested_includes, self.INCLUDE_RELATIONS
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

        transformation = self.get_transformation_for_action(
            principal=principal,
            uid=uid,
            action="view",
            select_related=select_paths,
            prefetch_related=["input_datastreams", *prefetch_paths],
        )

        return {
            "data": DataProductTransformationResponse.model_validate(transformation),
            "included": self.resolve_includes(
                [transformation], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: DataProductTransformationPostBody,
    ):
        if data.id is not None and data.id.version != 7:
            raise BadRequestError(f"Invalid UUID version {data.id.version}. Expected 7.")

        task = data_product_task_service.get_task_for_action(
            principal, data.task_id, action="view"
        )

        if not principal.can_create("DataProductTransformation", workspace=task.workspace):
            raise PermissionDeniedError(
                "You do not have permission to create transformations on this task."
            )

        transformation = DataProductTransformation(
            pk=data.id,
            task=task,
            transformation_type=data.transformation_type,
            **data.dict(
                include=set(DataProductTransformationFields.model_fields.keys())
                - {"input_datastreams"}
            ),
        )
        transformation.save()

        self.apply_input_datastreams(transformation, data.input_datastreams)

        transformation.full_clean()

        return {"id": transformation.pk}

    @transaction.atomic
    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: DataProductTransformationPatchBody,
    ):
        transformation = self.get_transformation_for_action(
            principal=principal, uid=uid, action="edit"
        )

        update_fields = data.dict(
            include=set(DataProductTransformationFields.model_fields.keys())
            - {"input_datastreams"},
            exclude_unset=True,
        )
        for field, value in update_fields.items():
            setattr(transformation, field, value)

        transformation.save()

        if data.input_datastreams is not Unset:
            self.apply_input_datastreams(transformation, data.input_datastreams)

        transformation.full_clean()

    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
    ):
        transformation = self.get_transformation_for_action(
            principal=principal, uid=uid, action="delete"
        )
        transformation.delete()

    @staticmethod
    def apply_input_datastreams(
        transformation: DataProductTransformation,
        input_datastreams: list[TransformationInputPostBody],
    ) -> None:
        transformation.input_datastreams.all().delete()

        for input_datastream in input_datastreams:
            new_input = DataProductTransformationInput(
                transformation=transformation,
                datastream_id=input_datastream.datastream_id,
                variable_name=input_datastream.variable_name,
            )
            new_input.full_clean()
            new_input.save()
