import uuid

from typing import Literal, Optional, get_args
from django.contrib.auth import get_user_model
from django.db import transaction

from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.types import Unset
from processing.products.models import DataProductTask, DataProductTransformation, DataProductTransformationInput
from interfaces.api.http.errors import BadRequestError, NotFoundError, PermissionDeniedError
from interfaces.api.service import APIService
from interfaces.api.schemas.products.transformation import (
    DataProductTransformationFields,
    DataProductTransformationSortByFields,
    DataProductTransformationPatchBody,
    DataProductTransformationPostBody,
    DataProductTransformationResponse,
    TransformationInputPostBody,
    DATA_PRODUCT_TRANSFORMATION_INCLUDE_RELATIONS,
)

User = get_user_model()


class DataProductTransformationAPIService(APIService):
    INCLUDE_RELATIONS = DATA_PRODUCT_TRANSFORMATION_INCLUDE_RELATIONS

    @staticmethod
    def get_task_for_action(
        principal: User | ServiceAccount | AnonymousPrincipal,
        task_id: uuid.UUID,
        action: Literal["view", "edit", "delete"],
    ) -> DataProductTask:
        try:
            task = DataProductTask.objects.select_related(
                "monitoring_site__workspace"
            ).get(pk=task_id)
        except DataProductTask.DoesNotExist:
            raise NotFoundError(f"Task with ID {task_id} does not exist.")

        if not principal.can_view(task):
            raise NotFoundError(f"Task with ID {task_id} does not exist.")

        if action != "view" and not getattr(principal, f"can_{action}")(task):
            raise PermissionDeniedError(
                f"You do not have permission to {action} transformations on this task."
            )

        return task

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
        task_id: uuid.UUID,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        select_related: Optional[list[str]] = None,
        prefetch_related: Optional[list[str]] = None,
    ) -> DataProductTransformation:
        task = self.get_task_for_action(principal, task_id, action)
        queryset = DataProductTransformation.objects.filter(task=task, pk=uid)

        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)

        try:
            return queryset.get()
        except DataProductTransformation.DoesNotExist:
            raise NotFoundError(f"DataProductTransformation with ID {uid} does not exist.")

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        task_id: uuid.UUID,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        sortby: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        task = self.get_task_for_action(principal, task_id, "view")
        queryset = DataProductTransformation.objects.filter(task=task)

        for field in [
            "transformation_type",
            "output_datastream_id",
            "input_datastreams__datastream_id",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        queryset = self.apply_sorting(
            queryset, sortby, list(get_args(DataProductTransformationSortByFields))
        )

        queryset = queryset.prefetch_related("input_datastreams")

        if requested_includes:
            select_paths, prefetch_paths = self._include_query_hints(requested_includes)
            queryset = queryset.select_related(*select_paths)
            if prefetch_paths:
                queryset = queryset.prefetch_related(*prefetch_paths)

        queryset = queryset.distinct()
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
        task_id: uuid.UUID,
        uid: uuid.UUID,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        select_paths, prefetch_paths = self._include_query_hints(requested_includes)

        transformation = self.get_transformation_for_action(
            principal=principal,
            task_id=task_id,
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
        task_id: uuid.UUID,
        data: DataProductTransformationPostBody,
    ):
        if data.id is not None and data.id.version != 7:
            raise BadRequestError(f"Invalid UUID version {data.id.version}. Expected 7.")

        task = self.get_task_for_action(principal, task_id, "edit")

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
        task_id: uuid.UUID,
        uid: uuid.UUID,
        data: DataProductTransformationPatchBody,
    ):
        transformation = self.get_transformation_for_action(
            principal=principal, task_id=task_id, uid=uid, action="edit"
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
        task_id: uuid.UUID,
        uid: uuid.UUID,
    ):
        transformation = self.get_transformation_for_action(
            principal=principal, task_id=task_id, uid=uid, action="delete"
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
