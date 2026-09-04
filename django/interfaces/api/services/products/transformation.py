import uuid
from typing import Union, Literal

from pydantic import BaseModel, Field, ConfigDict, validate_call
from django.db import transaction
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model

from core.types import Unset
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import BadRequestError, PermissionDeniedError, NotFoundError
from interfaces.api.service import APIService
from core.sta.models import Datastream
from processing.products.models import (
    DataProductTask, DataProductTransformation, DataProductTransformationInput, RatingCurve
)


User = get_user_model()

TransformationType = Literal["rating_curve", "derivation", "aggregation"]
AggregationMethod = Literal["mean", "sum", "min", "max", "first", "last", "time_weighted_mean"]
IntervalUnits = Literal["minutes", "hours", "days", "weeks", "months"]


class TransformationInput(BaseModel):
    datastream: Union[uuid.UUID, Datastream]
    variable_name: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class DataProductTransformationAPIService(APIService):

    order_by_fields = {"id", "transformation_type", "output_datastream_id"}

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal | Unset,
        action: Literal["view", "edit", "delete"],
        task: Union[uuid.UUID, DataProductTask],
        transformation: Union[uuid.UUID, DataProductTransformation],
    ) -> DataProductTransformation:
        """Get a data product transformation."""

        if isinstance(transformation, uuid.UUID):
            try:
                transformation = DataProductTransformation.objects.select_related(
                    "task__monitoring_site__workspace",
                    "output_datastream",
                    "rating_curve",
                ).prefetch_related(
                    "input_datastreams__datastream",
                    "rating_curve__points",
                ).get(pk=transformation, task=task)
            except DataProductTransformation.DoesNotExist:
                raise NotFoundError(
                    f"DataProductTransformation with ID {str(transformation)} does not exist."
                )

        if principal is not Unset:
            task_obj = principal.annotate_permissions(
                DataProductTask.objects.filter(pk=transformation.task_id)
            ).get()

            if not principal.can_view(task_obj):
                raise NotFoundError(
                    f"DataProductTransformation with ID {str(transformation.id)} does not exist."
                )

            if action != "view" and not getattr(principal, f"can_{action}")(task_obj):
                raise PermissionDeniedError(
                    f"You do not have permission to {action} this transformation."
                )

        return transformation

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal | Unset,
        task: Union[uuid.UUID, DataProductTask],
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] = Field(default_factory=list),
        transformation_type: list[str] | Unset = Unset,
        input_datastream: list[uuid.UUID] | Unset = Unset,
        output_datastream: list[uuid.UUID] | Unset = Unset,
    ) -> tuple[int, QuerySet[DataProductTransformation]]:
        """Return a collection of transformations of a task."""

        if isinstance(task, uuid.UUID):
            try:
                task = DataProductTask.objects.select_related("monitoring_site__workspace").get(pk=task)
            except DataProductTask.DoesNotExist:
                raise NotFoundError(f"Task with ID {str(task)} does not exist.")

        if principal is not Unset:
            if not principal.can_view(task):
                raise NotFoundError(f"Task with ID {str(task.id)} does not exist.")

        queryset = DataProductTransformation.objects.filter(task=task).select_related(
            "task__monitoring_site__workspace",
            "output_datastream",
            "rating_curve",
        ).prefetch_related(
            "input_datastreams__datastream",
            "rating_curve__points",
        )

        if transformation_type is not Unset:
            queryset = queryset.filter(transformation_type__in=transformation_type)

        if output_datastream is not Unset:
            queryset = queryset.filter(output_datastream__in=output_datastream)

        if input_datastream is not Unset:
            queryset = queryset.filter(input_datastreams__datastream__in=input_datastream)

        if not all(term.lstrip("-") in self.order_by_fields for term in order_by):
            raise BadRequestError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "id")

        count = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]

        return count, queryset

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        task: Union[uuid.UUID, DataProductTask],
        transformation_type: TransformationType,
        input_datastreams: list[TransformationInput],
        output_datastream: Union[uuid.UUID, Datastream],
        uid: uuid.UUID = Field(default_factory=uuid.uuid7),
        rating_curve: Union[uuid.UUID, RatingCurve] | Unset = Unset,
        formula: str | Unset = Unset,
        aggregation_method: AggregationMethod | Unset = Unset,
        output_interval_units: IntervalUnits | Unset = Unset,
        output_interval: int | Unset = Unset,
        timezone_type: str | None | Unset = Unset,
        timezone: str | None | Unset = Unset,
        min_values: int | None | Unset = Unset,
        stop_on_no_data: bool | Unset = Unset,
        stop_on_error: bool | Unset = Unset,
    ) -> DataProductTransformation:
        """Create a transformation for a task."""

        if uid.version != 7:
            raise BadRequestError(f"Invalid UUID version {uid.version}. Expected 7.")

        if isinstance(task, uuid.UUID):
            try:
                task = principal.annotate_permissions(
                    DataProductTask.objects.select_related("monitoring_site__workspace").filter(pk=task)
                ).get()
            except DataProductTask.DoesNotExist:
                raise NotFoundError(f"Task with ID {str(task)} does not exist.")

        if not principal.can_view(task):
            raise NotFoundError(f"Task with ID {str(task.id)} does not exist.")
        if not principal.can_edit(task):
            raise PermissionDeniedError("You do not have permission to edit this task.")

        transformation = DataProductTransformation(
            pk=uid,
            task=task,
            output_datastream_id=getattr(output_datastream, "pk", output_datastream),
            transformation_type=transformation_type,
            rating_curve_id=getattr(rating_curve, "pk", rating_curve) if rating_curve is not Unset else None,
            formula=formula if formula is not Unset else None,
            aggregation_method=aggregation_method if aggregation_method is not Unset else None,
            output_interval_units=output_interval_units if output_interval_units is not Unset else None,
            output_interval=output_interval if output_interval is not Unset else None,
            timezone_type=timezone_type if timezone_type is not Unset else None,
            timezone=timezone if timezone is not Unset else None,
            min_values=min_values if min_values is not Unset else None,
            stop_on_no_data=stop_on_no_data if stop_on_no_data is not Unset else True,
            stop_on_error=stop_on_error if stop_on_error is not Unset else True,
        )
        transformation.save()

        self.apply_input_datastreams(transformation, input_datastreams)

        transformation.full_clean()

        return self.get(principal=principal, action="view", transformation=transformation.pk, task=task)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal | Unset,
        task: Union[uuid.UUID, DataProductTask],
        transformation: Union[uuid.UUID, DataProductTransformation],
        input_datastreams: list[TransformationInput] | Unset = Unset,
        output_datastream: Union[uuid.UUID, Datastream] | Unset = Unset,
        rating_curve: Union[uuid.UUID, RatingCurve] | Unset = Unset,
        formula: str | Unset = Unset,
        aggregation_method: AggregationMethod | Unset = Unset,
        output_interval_units: IntervalUnits | Unset = Unset,
        output_interval: int | Unset = Unset,
        timezone_type: str | None | Unset = Unset,
        timezone: str | None | Unset = Unset,
        min_values: int | None | Unset = Unset,
        stop_on_no_data: bool | Unset = Unset,
        stop_on_error: bool | Unset = Unset,
    ) -> DataProductTransformation:
        """Update a transformation's parameters and inputs."""

        transformation = self.get(
            transformation=transformation, task=task, action="edit", principal=principal
        )

        editable_fields = {
            "output_datastream_id": getattr(output_datastream, "pk", output_datastream) if output_datastream is not Unset else Unset,
            "rating_curve_id": getattr(rating_curve, "pk", rating_curve) if rating_curve is not Unset else Unset,
            "formula": formula,
            "aggregation_method": aggregation_method,
            "output_interval_units": output_interval_units,
            "output_interval": output_interval,
            "timezone_type": timezone_type,
            "timezone": timezone,
            "min_values": min_values,
            "stop_on_no_data": stop_on_no_data,
            "stop_on_error": stop_on_error,
        }
        for field, value in editable_fields.items():
            if value is not Unset:
                setattr(transformation, field, value)

        transformation.save()

        if input_datastreams is not Unset:
            self.apply_input_datastreams(transformation, input_datastreams)

        transformation.full_clean()

        return self.get(principal=principal, action="view", transformation=transformation.pk, task=task)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal | Unset,
        task: Union[uuid.UUID, DataProductTask],
        transformation: Union[uuid.UUID, DataProductTransformation],
    ) -> None:
        """Delete a transformation."""

        transformation = self.get(
            transformation=transformation, task=task, action="delete", principal=principal
        )
        transformation.delete()

    @staticmethod
    def apply_input_datastreams(
        transformation: DataProductTransformation,
        input_datastreams: list[TransformationInput],
    ) -> None:
        """Associate input datastreams with a transformation."""

        transformation.input_datastreams.all().delete()

        for input_datastream in input_datastreams:
            new_input = DataProductTransformationInput(
                transformation=transformation,
                datastream_id=getattr(input_datastream.datastream, "pk", input_datastream.datastream),
                variable_name=input_datastream.variable_name,
            )
            new_input.full_clean()
            new_input.save()
