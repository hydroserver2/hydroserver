import uuid
import uuid6
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Union, Literal

from pydantic import BaseModel, Field, ConfigDict, validate_call
from django.db import transaction
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model

from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, normalize_tz
from hydroserverpy.products.expression import validate_expression, apply_expression
from hydroserverpy.products.aggregation import apply_aggregation
from hydroserverpy.products.rating_curve import apply_rating_curve

from core.types import Unset
from core.iam.models import APIKey
from core.service import ServiceUtils
from core.sta.models import Datastream
from core.sta.models.observation import Observation
from core.sta.services import ObservationService, DatastreamService
from interfaces.api.schemas import ObservationBulkPostBody
from processing.products.models import (
    DataProductTask, DataProductTransformation, DataProductTransformationInput, RatingCurve
)
from processing.products.services.rating_curve import RatingCurveService


User = get_user_model()

CHUNK_SIZE = 5000

logger = logging.getLogger(__name__)

datastream_service = DatastreamService()
observation_service = ObservationService()
rating_curve_service = RatingCurveService()

TransformationType = Literal["rating_curve", "expression", "composite_expression", "aggregation"]
AggregationMethod = Literal["mean", "sum", "min", "max", "first", "last"]
IntervalUnits = Literal["minutes", "hours", "days", "weeks", "months"]


class TransformationInput(BaseModel):
    datastream: Union[uuid.UUID, Datastream]
    variable_name: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TransformationInputPatch(BaseModel):
    datastream: Union[uuid.UUID, Datastream] | Unset = Unset
    variable_name: str | None | Unset = Unset

    model_config = ConfigDict(arbitrary_types_allowed=True)


_PERIOD_TO_UNIT = {"minutes": "min", "hours": "h", "days": "D"}
_UNIT_TO_DURATION = {"minutes": "m", "hours": "h", "days": "d", "weeks": "w"}
_UNIT_TO_SECONDS = {"minutes": 60, "hours": 3600, "days": 86400}


class DataProductTransformationService(ServiceUtils):

    order_by_fields = {"id", "transformation_type", "output_datastream_id"}

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        self,
        principal: User | APIKey | None | Unset,
        action: Literal["view", "edit", "delete"],
        task: Union[uuid.UUID, DataProductTask],
        transformation: Union[uuid.UUID, DataProductTransformation],
    ) -> DataProductTransformation:
        """Get a data product transformation."""

        if isinstance(transformation, uuid.UUID):
            try:
                transformation = DataProductTransformation.objects.select_related(
                    "task__thing__workspace",
                    "output_datastream",
                    "rating_curve",
                ).prefetch_related(
                    "input_datastreams__datastream",
                    "rating_curve__points",
                ).get(pk=transformation, task=task)
            except DataProductTransformation.DoesNotExist:
                raise LookupError(
                    f"DataProductTransformation with ID {str(transformation)} does not exist."
                )

        if principal is not Unset:
            permissions = transformation.task.get_principal_permissions(principal=principal)

            if "view" not in permissions:
                raise LookupError(
                    f"DataProductTransformation with ID {str(transformation.id)} does not exist."
                )

            if action not in permissions:
                raise PermissionError(
                    f"You do not have permission to {action} this transformation."
                )

        return transformation

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        principal: User | APIKey | None | Unset,
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
                task = DataProductTask.objects.select_related("thing__workspace").get(pk=task)
            except DataProductTask.DoesNotExist:
                raise LookupError(f"Task with ID {str(task)} does not exist.")

        if principal is not Unset:
            permissions = task.get_principal_permissions(principal=principal)
            if "view" not in permissions:
                raise LookupError(f"Task with ID {str(task.id)} does not exist.")

        queryset = DataProductTransformation.objects.filter(task=task).select_related(
            "task__thing__workspace",
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
            raise ValueError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "id")

        count = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]

        return count, queryset

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | APIKey | None | Unset,
        task: Union[uuid.UUID, DataProductTask],
        transformation_type: TransformationType,
        input_datastreams: list[TransformationInput],
        output_datastream: Union[uuid.UUID, Datastream],
        uid: uuid.UUID = Field(default_factory=uuid6.uuid7),
        rating_curve: Union[uuid.UUID, RatingCurve] | Unset = Unset,
        formula: str | Unset = Unset,
        aggregation_method: AggregationMethod | Unset = Unset,
        output_interval_units: IntervalUnits | Unset = Unset,
        output_interval: int | Unset = Unset,
        timezone_type: str | None | Unset = Unset,
        timezone: str | None | Unset = Unset,
        max_gap_interval: int | None | Unset = Unset,
        max_gap_interval_units: IntervalUnits | None | Unset = Unset,
        min_values: int | None | Unset = Unset,
    ) -> DataProductTransformation:
        """Create a transformation for a task."""

        if uid.version != 7:
            raise ValueError(f"Invalid UUID version {uid.version}. Expected 7.")

        if isinstance(task, uuid.UUID):
            try:
                task = DataProductTask.objects.select_related("thing__workspace").get(pk=task)
            except DataProductTask.DoesNotExist:
                raise LookupError(f"Task with ID {str(task)} does not exist.")

        permissions = task.get_principal_permissions(principal=principal)

        if "view" not in permissions:
            raise LookupError(f"Task with ID {str(task.id)} does not exist.")
        if "edit" not in permissions:
            raise PermissionError("You do not have permission to edit this task.")

        self.validate_transformation(
            task=task,
            transformation_type=transformation_type,
            input_datastreams=input_datastreams,
            output_datastream=output_datastream,
            rating_curve=rating_curve,
            formula=formula,
            aggregation_method=aggregation_method,
            output_interval_units=output_interval_units,
            output_interval=output_interval,
            timezone_type=timezone_type,
            timezone=timezone,
            max_gap_interval=max_gap_interval,
            max_gap_interval_units=max_gap_interval_units,
            min_values=min_values,
        )

        transformation = DataProductTransformation.objects.create(
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
            max_gap_interval=max_gap_interval if max_gap_interval is not Unset else None,
            max_gap_interval_units=max_gap_interval_units if max_gap_interval_units is not Unset else None,
            min_values=min_values if min_values is not Unset else None,
        )

        self.apply_input_datastreams(transformation, input_datastreams)

        return self.get(principal=principal, action="view", transformation=transformation.pk, task=task)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        principal: User | APIKey | None | Unset,
        task: Union[uuid.UUID, DataProductTask],
        transformation: Union[uuid.UUID, DataProductTransformation],
        input_datastreams: list[Union[TransformationInput, TransformationInputPatch]] | Unset = Unset,
        output_datastream: Union[uuid.UUID, Datastream] | Unset = Unset,
        rating_curve: Union[uuid.UUID, RatingCurve] | Unset = Unset,
        formula: str | Unset = Unset,
        aggregation_method: AggregationMethod | Unset = Unset,
        output_interval_units: IntervalUnits | Unset = Unset,
        output_interval: int | Unset = Unset,
        timezone_type: str | Unset = Unset,
        timezone: str | None | Unset = Unset,
        max_gap_interval: int | None | Unset = Unset,
        max_gap_interval_units: IntervalUnits | None | Unset = Unset,
        min_values: int | None | Unset = Unset,
    ) -> DataProductTransformation:
        """Update a transformation's parameters and inputs."""

        transformation = self.get(
            transformation=transformation, task=task, action="edit", principal=principal
        )

        transformation_type: TransformationType = transformation.transformation_type  # type: ignore[assignment]

        if input_datastreams is not Unset and any(
            isinstance(inp, TransformationInputPatch) for inp in input_datastreams
        ):
            existing_inputs = list(transformation.input_datastreams.select_related("datastream").all())
            input_datastreams = [
                TransformationInput(
                    datastream=(
                        inp.datastream if inp.datastream is not Unset
                        else existing_inputs[i].datastream
                    ),
                    variable_name=(
                        inp.variable_name if inp.variable_name is not Unset
                        else (existing_inputs[i].variable_name if i < len(existing_inputs) else None)
                    ),
                ) if isinstance(inp, TransformationInputPatch) else inp
                for i, inp in enumerate(input_datastreams)
            ]

        self.validate_transformation(
            task=task,
            transformation_type=transformation_type,
            input_datastreams=(
                input_datastreams if input_datastreams is not Unset else transformation.input_datastreams.all()
            ),
            output_datastream=output_datastream if output_datastream is not Unset else transformation.output_datastream,
            rating_curve=(
                rating_curve if rating_curve is not Unset
                else (transformation.rating_curve_id if transformation_type == "rating_curve" else Unset)
            ),
            formula=(
                formula if formula is not Unset
                else (
                    transformation.formula if transformation_type in ("expression", "composite_expression") else Unset
                )
            ),
            aggregation_method=(
                aggregation_method if aggregation_method is not Unset
                else (transformation.aggregation_method if transformation_type == "aggregation" else Unset)
            ),
            output_interval_units=(
                output_interval_units if output_interval_units is not Unset
                else (
                    transformation.output_interval_units
                    if transformation_type in ("aggregation", "composite_expression") else Unset
                )
            ),
            output_interval=(
                output_interval if output_interval is not Unset
                else (
                    transformation.output_interval
                    if transformation_type in ("aggregation", "composite_expression") else Unset
                )
            ),
            timezone_type=(
                timezone_type if timezone_type is not Unset
                else (transformation.timezone_type if transformation_type == "aggregation" else Unset)
            ),
            timezone=(
                timezone if timezone is not Unset
                else (transformation.timezone if transformation_type == "aggregation" else Unset)
            ),
            max_gap_interval=(
                max_gap_interval if max_gap_interval is not Unset
                else (transformation.max_gap_interval if transformation_type == "composite_expression" else Unset)
            ),
            max_gap_interval_units=(
                max_gap_interval_units if max_gap_interval_units is not Unset
                else (transformation.max_gap_interval_units if transformation_type == "composite_expression" else Unset)
            ),
            min_values=(
                min_values if min_values is not Unset
                else (transformation.min_values if transformation_type == "aggregation" else Unset)
            ),
        )

        editable_fields = {
            "output_datastream_id": getattr(output_datastream, "pk", output_datastream),
            "rating_curve_id": getattr(rating_curve, "pk", rating_curve),
            "formula": formula,
            "aggregation_method": aggregation_method,
            "output_interval_units": output_interval_units,
            "output_interval": output_interval,
            "timezone_type": timezone_type,
            "timezone": timezone,
            "max_gap_interval": max_gap_interval,
            "max_gap_interval_units": max_gap_interval_units,
            "min_values": min_values,
        }
        for field, value in editable_fields.items():
            if value is not Unset:
                setattr(transformation, field, value)

        transformation.save()

        if input_datastreams is not Unset:
            self.apply_input_datastreams(transformation, input_datastreams)

        return self.get(principal=principal, action="view", transformation=transformation.pk, task=task)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def delete(
        self,
        principal: User | APIKey | None | Unset,
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
        DataProductTransformationInput.objects.bulk_create([
            DataProductTransformationInput(
                transformation=transformation,
                datastream_id=getattr(input_datastream.datastream, "pk", input_datastream.datastream),
                variable_name=input_datastream.variable_name,
            )
            for input_datastream in input_datastreams
        ])

    @staticmethod
    def validate_transformation(
        task: Union[uuid.UUID, DataProductTask],
        transformation_type: TransformationType,
        input_datastreams: list[TransformationInput],
        output_datastream: Union[uuid.UUID, Datastream],
        rating_curve: Union[uuid.UUID, RatingCurve] | Unset = Unset,
        formula: str | Unset = Unset,
        aggregation_method: AggregationMethod | Unset = Unset,
        output_interval_units: IntervalUnits | Unset = Unset,
        output_interval: int | Unset = Unset,
        timezone_type: str | Unset = Unset,
        timezone: str | None | Unset = Unset,
        max_gap_interval: int | None | Unset = Unset,
        max_gap_interval_units: IntervalUnits | None | Unset = Unset,
        min_values: int | None | Unset = Unset,
    ) -> None:
        """Validate transformation parameters and raise ValueError if invalid."""

        if isinstance(task, uuid.UUID):
            try:
                task = DataProductTask.objects.select_related("thing__workspace").get(pk=task)
            except DataProductTask.DoesNotExist:
                raise LookupError(f"Task with ID {str(task)} does not exist.")

        workspace = task.thing.workspace
        thing = task.thing
        input_datastream_variable_names = []

        for input_datastream in input_datastreams:
            if isinstance(input_datastream.datastream, uuid.UUID):
                try:
                    input_datastream_obj = Datastream.objects.select_related("thing__workspace").get(
                        pk=input_datastream.datastream
                    )
                except Datastream.DoesNotExist:
                    raise LookupError(f"Datastream with ID {str(input_datastream.datastream)} does not exist.")
            else:
                input_datastream_obj = input_datastream.datastream

            if input_datastream_obj.thing.workspace != workspace:
                raise ValueError(
                    f"Datastream with ID {str(input_datastream_obj.id)} does not belong to workspace "
                    f"{workspace.id}."
                )

            if (variable_name := input_datastream.variable_name) is not None:
                if variable_name in input_datastream_variable_names:
                    raise ValueError(f"Duplicate variable_name '{variable_name}'.")
                input_datastream_variable_names.append(variable_name)

        if isinstance(output_datastream, uuid.UUID):
            try:
                output_datastream_obj = Datastream.objects.select_related("thing__workspace").get(
                    pk=output_datastream
                )
            except Datastream.DoesNotExist:
                raise LookupError(f"Datastream with ID {str(output_datastream)} does not exist.")
        else:
            output_datastream_obj = output_datastream

        if output_datastream_obj.thing.workspace != workspace:
            raise ValueError(
                f"Datastream with ID {str(output_datastream_obj.id)} does not belong to workspace "
                f"{workspace.id}."
            )
        if output_datastream_obj.thing != thing:
            raise ValueError(
                f"Datastream with ID {str(output_datastream_obj.id)} does not belong to thing "
                f"{thing.id}."
            )

        if transformation_type == "rating_curve":
            if rating_curve is Unset:
                raise ValueError("rating_curve is required for transformation_type 'rating_curve'.")
            if any(v is not Unset for v in (
                formula, output_interval_units, output_interval, aggregation_method, max_gap_interval,
                max_gap_interval_units, min_values
            )):
                raise ValueError(
                    "formula, output_interval_units, output_interval, and aggregation_method must not be set "
                    "for transformation_type 'rating_curve'."
                )
            try:
                RatingCurve.objects.get(
                    pk=getattr(rating_curve, "pk", rating_curve), thing=task.thing
                )
            except RatingCurve.DoesNotExist:
                raise LookupError(
                    f"Rating curve with ID {str(output_datastream)} does not exist at site {task.thing.id}."
                )

        elif transformation_type == "expression":
            if formula is Unset:
                raise ValueError("formula is required for transformation_type 'expression'.")
            if any(v is not Unset for v in (
                rating_curve, output_interval_units, output_interval, aggregation_method, max_gap_interval,
                max_gap_interval_units, min_values
            )):
                raise ValueError(
                    "rating_curve_id, output_interval_units, output_interval, and aggregation_method must not be set "
                    "for transformation_type 'expression'."
                )
            validate_expression(
                formula=formula,
                variables=input_datastream_variable_names
            )

        elif transformation_type == "composite_expression":
            if any(v is Unset for v in (formula, output_interval_units, output_interval)):
                raise ValueError(
                    "formula, output_interval_units, and output_interval are required "
                    "for transformation_type 'composite_expression'."
                )
            if any(v is not Unset for v in (rating_curve, aggregation_method, min_values)):
                raise ValueError(
                    "rating_curve_id, min_values, and aggregation_method must not be set "
                    "for transformation_type 'composite_expression'."
                )
            if (max_gap_interval is Unset) != (max_gap_interval_units is Unset):
                raise ValueError(
                    "max_gap_interval and max_gap_interval_units must both be set or both be unset."
                )
            if len(input_datastreams) < 2:
                raise ValueError(
                    "composite_expression requires at least 2 inputs. "
                    "Use 'expression' for single-input transformations."
                )
            validate_expression(
                formula=formula,
                variables=input_datastream_variable_names
            )

        elif transformation_type == "aggregation":
            if any(v is Unset for v in (aggregation_method, output_interval_units, output_interval)):
                raise ValueError(
                    "aggregation_method, output_interval_units, and output_interval are required for "
                    "transformation_type 'aggregation'."
                )
            if any(v is not Unset for v in (rating_curve, formula, max_gap_interval, max_gap_interval_units)):
                raise ValueError(
                    "rating_curve, formula, max_gap_interval, and max_gap_interval_units must not be set "
                    "for transformation_type 'aggregation'."
                )

            is_tz_type_set = timezone_type is not Unset and timezone_type is not None
            is_tz_set = timezone is not Unset and timezone is not None

            if is_tz_set and not is_tz_type_set:
                raise ValueError("timezone_type is required when timezone is set.")

            if is_tz_type_set:
                if timezone_type == "utc":
                    if is_tz_set:
                        raise ValueError("timezone must not be set when timezone_type is 'utc'.")
                elif timezone_type == "iana":
                    if not is_tz_set:
                        raise ValueError("timezone is required when timezone_type is 'iana'.")
                    normalize_tz(timezone)
                elif timezone_type == "offset":
                    if not is_tz_set:
                        raise ValueError("timezone is required when timezone_type is 'offset'.")
                    normalize_tz(timezone)

        else:
            raise ValueError(f"Invalid transformation_type '{transformation_type}'.")

    def run(self, transformation: DataProductTransformation) -> int:
        """Dispatch to the appropriate transformation run method."""

        if transformation.transformation_type == "rating_curve":
            return self.run_rating_curve(transformation)
        elif transformation.transformation_type == "expression":
            return self.run_expression(transformation)
        elif transformation.transformation_type == "composite_expression":
            return self.run_composite_expression(transformation)
        elif transformation.transformation_type == "aggregation":
            return self.run_aggregation(transformation)
        else:
            raise ValueError(f"Unknown transformation_type: {transformation.transformation_type}")

    def run_rating_curve(self, transformation: DataProductTransformation) -> int:
        """
        Apply a rating curve to a single input datastream and load results to the output datastream.

        Observations outside the curve's valid range are dropped. The polynomial fitting method
        is not supported and will be skipped with a warning.
        """

        input_entry = transformation.input_datastreams.first()
        if input_entry is None:
            return 0

        rating_curve = transformation.rating_curve
        if rating_curve is None:
            return 0

        input_ds = input_entry.datastream
        output_ds = transformation.output_datastream

        start = output_ds.phenomenon_end_time
        end = input_ds.phenomenon_end_time

        if end is None:
            return 0
        if start is not None and end <= start:
            return 0

        input_df = self._fetch_observations(input_ds, after=start, through=end)
        if len(input_df) == 0:
            return 0

        breakpoints = [
            (point.input_value, point.output_value)
            for point in rating_curve.points.all()
        ]

        result_df = apply_rating_curve(
            input_df,
            breakpoints=breakpoints,
            method=rating_curve.fitting_method,  # noqa
            out_of_range="ndv",
            no_data_value=input_ds.no_data_value,
        )

        if len(result_df) == 0:
            return 0

        return self._load_to_datastream(transformation, result_df)

    def run_expression(self, transformation: DataProductTransformation) -> int:
        """
        Evaluate a formula against a single input datastream and load results to the output datastream.
        """

        input_entry = transformation.input_datastreams.first()
        if input_entry is None:
            return 0

        input_ds = input_entry.datastream
        output_ds = transformation.output_datastream
        variable_name = input_entry.variable_name or RESULT_COL

        start = output_ds.phenomenon_end_time
        end = input_ds.phenomenon_end_time

        if end is None:
            return 0
        if start is not None and end <= start:
            return 0

        input_df = self._fetch_observations(input_ds, after=start, through=end)
        if len(input_df) == 0:
            return 0

        result_df = apply_expression(
            inputs={variable_name: input_df},
            formula=transformation.formula,
            no_data_value=input_ds.no_data_value,
        )

        if len(result_df) == 0:
            return 0

        return self._load_to_datastream(transformation, result_df)

    def run_composite_expression(self, transformation: DataProductTransformation) -> int:
        """
        Interpolate multiple input datastreams onto a shared time grid, evaluate a formula
        against each row, and load results to the output datastream.
        """

        if transformation.output_interval_units not in _UNIT_TO_DURATION:
            raise NotImplementedError(
                f"Interval unit '{transformation.output_interval_units}' is not supported. "
                f"Supported units: {', '.join(_UNIT_TO_DURATION)}."
            )

        input_entries = list(transformation.input_datastreams.select_related("datastream").all())
        if not input_entries:
            return 0

        output_ds = transformation.output_datastream
        interval = f"{transformation.output_interval}{_UNIT_TO_DURATION[transformation.output_interval_units]}"

        # Limit end at the earliest input's phenomenon_end_time so we only
        # interpolate where all inputs have data.
        input_ends = [entry.datastream.phenomenon_end_time for entry in input_entries]
        if any(e is None for e in input_ends):
            return 0
        end = min(input_ends)

        start = output_ds.phenomenon_end_time
        if start is not None and end <= start:
            return 0

        max_gap = None
        if transformation.max_gap_interval is not None and transformation.max_gap_interval_units is not None:
            if transformation.max_gap_interval_units not in _UNIT_TO_DURATION:
                raise NotImplementedError(
                    f"max_gap interval unit '{transformation.max_gap_interval_units}' is not supported. "
                    f"Supported units: {', '.join(_UNIT_TO_DURATION)}."
                )
            max_gap = f"{transformation.max_gap_interval}{_UNIT_TO_DURATION[transformation.max_gap_interval_units]}"

        inputs = {}
        for entry in input_entries:
            df = self._fetch_observations(entry.datastream, after=start, through=end)
            if len(df) == 0:
                return 0
            inputs[entry.variable_name] = df

        result_df = apply_expression(
            inputs=inputs,
            formula=transformation.formula,
            interval=interval,
            on_missing="interpolate",
            max_gap=max_gap,
            no_data_value=input_entries[0].datastream.no_data_value,
        )

        if len(result_df) == 0:
            return 0

        return self._load_to_datastream(transformation, result_df)

    def run_aggregation(self, transformation: DataProductTransformation) -> int:
        """
        Resample a single input datastream into fixed time periods using the configured
        aggregation method and load results to the output datastream.
        """

        if transformation.output_interval_units not in _UNIT_TO_DURATION:
            raise NotImplementedError(
                f"Interval unit '{transformation.output_interval_units}' is not supported for aggregation. "
                f"Supported units: {', '.join(_UNIT_TO_DURATION)}."
            )

        input_entry = transformation.input_datastreams.first()
        if input_entry is None:
            return 0

        input_ds = input_entry.datastream
        output_ds = transformation.output_datastream

        interval = f"{transformation.output_interval}{_UNIT_TO_DURATION[transformation.output_interval_units]}"
        local_timezone = (
            transformation.timezone
            if transformation.timezone_type and transformation.timezone_type != "utc"
            else None
        )

        # Advance raw_start to the next aligned period boundary so we never
        # re-aggregate a period already present in the output datastream.
        raw_start = output_ds.phenomenon_end_time
        if raw_start is not None:
            from hydroserverpy.core.duration import duration_to_us
            epoch = datetime(1970, 1, 1, tzinfo=dt_timezone.utc)
            interval_us = duration_to_us(interval)
            raw_start_utc = raw_start if raw_start.tzinfo else raw_start.replace(tzinfo=dt_timezone.utc)
            raw_start_us = int((raw_start_utc - epoch).total_seconds() * 1_000_000)
            start_us = ((raw_start_us // interval_us) + 1) * interval_us
            start = epoch + timedelta(microseconds=start_us)
        else:
            start = None

        end = input_ds.phenomenon_end_time

        if end is None:
            return 0
        if start is not None and end <= start:
            return 0

        input_df = self._fetch_observations(input_ds, after=start, through=end)
        if len(input_df) == 0:
            return 0

        result_df = apply_aggregation(
            input_df,
            interval=interval,
            method=transformation.aggregation_method,  # noqa
            local_timezone=local_timezone,
            min_values=transformation.min_values,
            on_sparse="ndv",
            no_data_value=input_ds.no_data_value,
        )

        # Discard the last bucket if its end extends beyond the available input data,
        # as it may be incomplete (i.e., the current period is still in progress).
        if len(result_df) > 0:
            from hydroserverpy.core.duration import duration_to_us
            interval_us = duration_to_us(interval)
            end_utc = end if end.tzinfo else end.replace(tzinfo=dt_timezone.utc)
            result_df = result_df[
                result_df[TIMESTAMP_COL] + pd.Timedelta(microseconds=interval_us) <= end_utc
            ].reset_index(drop=True)

        if len(result_df) == 0:
            return 0

        return self._load_to_datastream(transformation, result_df)

    @staticmethod
    def _fetch_observations(
        datastream: Datastream,
        after=None,
        through=None,
    ) -> pd.DataFrame:
        """
        Fetch observations for a datastream as a canonical pandas timeseries DataFrame.
        """

        qs = Observation.objects.filter(datastream=datastream).order_by("phenomenon_time")

        if after is not None:
            qs = qs.filter(phenomenon_time__gt=after)
        if through is not None:
            qs = qs.filter(phenomenon_time__lte=through)

        data = list(qs.values_list("phenomenon_time", "result"))

        if not data:
            return pd.DataFrame({
                TIMESTAMP_COL: pd.Series([], dtype="datetime64[us, UTC]"),
                RESULT_COL: pd.Series([], dtype=np.float64),
            })

        timestamps, results = zip(*data)

        return pd.DataFrame({
            TIMESTAMP_COL: pd.DatetimeIndex(timestamps).as_unit("us"),
            RESULT_COL: np.array(results, dtype=np.float64),
        })

    @staticmethod
    def _load_to_datastream(
        transformation: DataProductTransformation,
        result_df: pd.DataFrame,
    ) -> int:
        """
        Write a canonical pandas timeseries DataFrame to the output datastream.
        Uses the task's workspace owner as the principal.
        """

        output_ds = transformation.output_datastream
        principal = transformation.task.thing.workspace.owner

        data = list(zip(
            result_df[TIMESTAMP_COL].tolist(),
            result_df[RESULT_COL].tolist(),
        ))
        loaded = 0

        for i in range(0, len(data), CHUNK_SIZE):
            chunk = data[i:i + CHUNK_SIZE]
            observation_service.bulk_create(
                principal=principal,
                data=ObservationBulkPostBody(
                    fields=["phenomenonTime", "result"],
                    data=chunk,
                ),
                datastream_id=output_ds.pk,
                mode="append",
            )
            loaded += len(chunk)

        logger.info("Loaded %s observation(s) to datastream %s.", loaded, output_ds.pk)

        return loaded
