import logging
import numpy as np
import pandas as pd

from datetime import datetime, timedelta, timezone as dt_timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from celery import shared_task

from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, normalize_tz
from hydroserverpy.core.duration import duration_to_us
from hydroserverpy.products.derivation import apply_derivation
from hydroserverpy.products.aggregation import apply_aggregation
from hydroserverpy.products.rating_curve import apply_rating_curve

from core.sta.models import Datastream
from core.sta.models.observation import Observation
from interfaces.api.services.sta import DatastreamAPIService, ObservationAPIService
from interfaces.api.schemas import ObservationBulkPostBody
from processing.products.exceptions import DataProductError
from processing.products.models import DataProductTask, DataProductTransformation


CHUNK_SIZE = 5000

logger = logging.getLogger(__name__)

datastream_service = DatastreamAPIService()
observation_service = ObservationAPIService()

UNIT_TO_DURATION = {"minutes": "m", "hours": "h", "days": "d", "weeks": "w"}


def run_transformation(transformation: DataProductTransformation) -> int:
    """Dispatch to the appropriate transformation run method."""

    if transformation.transformation_type == "rating_curve":
        return run_rating_curve(transformation)
    elif transformation.transformation_type == "derivation":
        return run_derivation(transformation)
    elif transformation.transformation_type == "aggregation":
        return run_aggregation(transformation)
    else:
        raise ValueError(f"Unknown transformation_type: {transformation.transformation_type}")


def run_rating_curve(transformation: DataProductTransformation) -> int:
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

    input_df = _fetch_observations(input_ds, after=start, through=end)
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

    return _load_to_datastream(transformation, result_df)


def run_derivation(transformation: DataProductTransformation) -> int:
    """
    Evaluate a formula against one or more input datastreams and load results
    to the output datastream.
    """

    input_entries = list(transformation.input_datastreams.select_related("datastream").all())
    if not input_entries:
        return 0

    output_ds = transformation.output_datastream

    input_ends = [entry.datastream.phenomenon_end_time for entry in input_entries]
    if any(e is None for e in input_ends):
        return 0
    end = min(input_ends)

    start = output_ds.phenomenon_end_time
    if start is not None and end <= start:
        return 0

    inputs = {}
    input_no_data_values = {}
    for entry in input_entries:
        df = _fetch_observations(entry.datastream, after=start, through=end)
        if len(df) == 0:
            return 0
        inputs[entry.variable_name] = df
        input_no_data_values[entry.variable_name] = entry.datastream.no_data_value

    result_df = apply_derivation(
        inputs=inputs,
        formula=transformation.formula,
        stop_on_no_data=transformation.stop_on_no_data,
        stop_on_error=transformation.stop_on_error,
        input_no_data_values=input_no_data_values,
        output_no_data_value=output_ds.no_data_value,
    )

    if len(result_df) == 0:
        return 0

    return _load_to_datastream(transformation, result_df)


def run_aggregation(transformation: DataProductTransformation) -> int:
    """
    Resample a single input datastream into fixed time periods using the configured
    aggregation method and load results to the output datastream.
    """

    if transformation.output_interval_units not in UNIT_TO_DURATION:
        raise NotImplementedError(
            f"Interval unit '{transformation.output_interval_units}' is not supported for aggregation. "
            f"Supported units: {', '.join(UNIT_TO_DURATION)}."
        )

    input_entry = transformation.input_datastreams.first()
    if input_entry is None:
        return 0

    input_ds = input_entry.datastream
    output_ds = transformation.output_datastream

    interval = f"{transformation.output_interval}{UNIT_TO_DURATION[transformation.output_interval_units]}"
    local_timezone = (
        transformation.timezone
        if transformation.timezone_type and transformation.timezone_type != "utc"
        else None
    )

    # Advance raw_start to the next aligned period boundary so we never
    # re-aggregate a period already present in the output datastream.
    raw_start = output_ds.phenomenon_end_time
    if raw_start is not None:
        epoch = datetime(1970, 1, 1, tzinfo=dt_timezone.utc)
        interval_us = duration_to_us(interval)
        raw_start_utc = raw_start if raw_start.tzinfo else raw_start.replace(tzinfo=dt_timezone.utc)
        raw_start_us = int((raw_start_utc - epoch).total_seconds() * 1_000_000)
        if local_timezone:
            tz = ZoneInfo(normalize_tz(local_timezone))
            utc_offset_us = int(raw_start_utc.astimezone(tz).utcoffset().total_seconds() * 1_000_000)
        else:
            utc_offset_us = 0
        local_midnight_us = -utc_offset_us
        start_us = local_midnight_us + ((raw_start_us - local_midnight_us) // interval_us + 1) * interval_us
        start = epoch + timedelta(microseconds=start_us)
    else:
        start = None

    end = input_ds.phenomenon_end_time

    if end is None:
        return 0
    if start is not None and end <= start:
        return 0

    input_df = _fetch_observations(input_ds, after=start, through=end)
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
        interval_us = duration_to_us(interval)
        end_utc = end if end.tzinfo else end.replace(tzinfo=dt_timezone.utc)
        result_df = result_df[
            result_df[TIMESTAMP_COL] + pd.Timedelta(microseconds=interval_us) <= end_utc
        ].reset_index(drop=True)

    if len(result_df) == 0:
        return 0

    return _load_to_datastream(transformation, result_df)


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


def _load_to_datastream(
    transformation: DataProductTransformation,
    result_df: pd.DataFrame,
) -> int:
    """
    Write a canonical pandas timeseries DataFrame to the output datastream.
    Uses the task's workspace owner as the principal.
    """

    output_ds = transformation.output_datastream
    principal = transformation.task.monitoring_site.workspace.owner

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


@shared_task(bind=True, name="processing.products.tasks.run_data_product_task")
def run_data_product_task(self, task_id: str, run_id: str | None = None):
    """
    Runs a HydroServer data product task based on the task configuration provided.
    """

    try:
        try:
            task = DataProductTask.objects.get(pk=UUID(task_id))
        except DataProductTask.DoesNotExist:
            raise LookupError(f"Data product task with ID {task_id} does not exist.")

        transformations = list(
            task.transformations
            .select_related("output_datastream", "rating_curve", "task__monitoring_site__workspace__owner")
            .prefetch_related("input_datastreams__datastream", "rating_curve__points")
        )

        loaded_total = 0
        success_count = 0
        errors = {}

        for transformation in transformations:
            try:
                loaded = run_transformation(transformation)
                loaded_total += loaded
                success_count += 1
            except Exception as e:
                errors[str(transformation.id)] = (
                    str(e) if isinstance(e, ValueError) else "Encountered an unexpected error."
                )
                logger.error(
                    "Failed to run transformation %s (%s → %s)",
                    transformation.id,
                    transformation.transformation_type,
                    transformation.output_datastream_id,
                    exc_info=True,
                )

        total = len(transformations)
        failure_count = len(errors)

        if not errors:
            if loaded_total == 0:
                message = "Already up-to-date. No new observations were loaded."
            else:
                message = f"Loaded {loaded_total} observation(s) across {success_count} transformation(s)."
        else:
            if loaded_total == 0:
                message = f"{failure_count} of {total} transformation(s) failed. No observations were loaded."
            else:
                message = (
                    f"Loaded {loaded_total} observation(s) across {success_count} of {total} transformation(s). "
                    f"{failure_count} transformation(s) failed."
                )

        if errors:
            exc = DataProductError(message)
            exc.result = {"loaded_total": loaded_total, "errors": errors}
            raise exc

        result = {"message": message, "loaded_total": loaded_total, "errors": errors}
    except DataProductError as e:
        raise e
    except Exception as e:
        raise Exception("Encountered an unexpected data product error.") from e

    return result
