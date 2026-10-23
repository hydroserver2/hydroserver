import uuid
from unittest.mock import patch

import pandas as pd
import pytest

from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL
from core.sta.models import Observation
from hydroserverpy.products.aggregation import apply_aggregation
from processing.products.tasks import (
    _fetch_observations,
    _load_to_datastream,
    run_data_product_task,
)
from tests.core.sta.factories import DatastreamFactory, ObservationFactory
from tests.processing.products.factories import (
    DataProductTransformationFactory,
    DataProductTransformationInputFactory,
    RatingCurveFactory,
    RatingCurvePointFactory,
)

pytestmark = pytest.mark.django_db


def test_run_data_product_task_raises_for_nonexistent_task():
    with pytest.raises(Exception, match="Encountered an unexpected data product error."):
        run_data_product_task(str(uuid.uuid4()))


@pytest.mark.parametrize("min_values", [None, 2])
def test_incremental_aggregation_includes_observation_at_next_bucket_start(min_values):
    output_ds = DatastreamFactory()
    input_ds = DatastreamFactory(
        monitoring_site=output_ds.monitoring_site,
        phenomenon_end_time=pd.Timestamp("2026-01-01T01:00:00Z"),
    )
    transformation = DataProductTransformationFactory(
        task__monitoring_site=output_ds.monitoring_site,
        output_datastream=output_ds,
        transformation_type="aggregation",
        formula=None,
        output_interval=1,
        output_interval_units="hours",
        aggregation_method="sum",
        min_values=min_values,
    )
    DataProductTransformationInputFactory(
        transformation=transformation, datastream=input_ds
    )
    for timestamp, value in [
        ("2026-01-01T00:00:00Z", 1.0),
        ("2026-01-01T00:30:00Z", 2.0),
        ("2026-01-01T01:00:00Z", 100.0),
    ]:
        ObservationFactory(
            datastream=input_ds, phenomenon_time=pd.Timestamp(timestamp), result=value
        )

    first_run = run_data_product_task(str(transformation.task_id))

    assert first_run["loaded_total"] == 1
    assert first_run["errors"] == {}
    assert list(Observation.objects.filter(datastream=output_ds).values_list(
        "phenomenon_time", "result"
    )) == [(pd.Timestamp("2026-01-01T00:00:00Z"), 3.0)]

    for timestamp, value in [
        ("2026-01-01T01:30:00Z", 2.0),
        ("2026-01-01T02:00:00Z", 0.0),
    ]:
        ObservationFactory(
            datastream=input_ds, phenomenon_time=pd.Timestamp(timestamp), result=value
        )
    input_ds.phenomenon_end_time = pd.Timestamp("2026-01-01T02:00:00Z")
    input_ds.save(update_fields=["phenomenon_end_time"])

    second_run = run_data_product_task(str(transformation.task_id))

    assert second_run["loaded_total"] == 1
    assert second_run["errors"] == {}
    assert list(Observation.objects.filter(datastream=output_ds).order_by(
        "phenomenon_time"
    ).values_list("phenomenon_time", "result")) == [
        (pd.Timestamp("2026-01-01T00:00:00Z"), 3.0),
        (pd.Timestamp("2026-01-01T01:00:00Z"), 102.0),
    ]
    assert run_data_product_task(str(transformation.task_id))["loaded_total"] == 0


def test_incremental_time_weighted_mean_interpolates_from_previous_observation():
    output_ds = DatastreamFactory()
    input_ds = DatastreamFactory(
        monitoring_site=output_ds.monitoring_site,
        phenomenon_end_time=pd.Timestamp("2026-01-01T01:20:00Z"),
    )
    transformation = DataProductTransformationFactory(
        task__monitoring_site=output_ds.monitoring_site,
        output_datastream=output_ds,
        transformation_type="aggregation",
        formula=None,
        output_interval=1,
        output_interval_units="hours",
        aggregation_method="time_weighted_mean",
        min_values=None,
    )
    DataProductTransformationInputFactory(
        transformation=transformation, datastream=input_ds
    )
    for timestamp, value in [
        ("2026-01-01T00:00:00Z", 0.0),
        ("2026-01-01T00:40:00Z", 4.0),
        ("2026-01-01T01:20:00Z", 8.0),
    ]:
        ObservationFactory(
            datastream=input_ds, phenomenon_time=pd.Timestamp(timestamp), result=value
        )

    assert run_data_product_task(str(transformation.task_id))["loaded_total"] == 1

    for timestamp, value in [
        ("2026-01-01T01:50:00Z", 2.0),
        ("2026-01-01T02:10:00Z", 2.0),
    ]:
        ObservationFactory(
            datastream=input_ds, phenomenon_time=pd.Timestamp(timestamp), result=value
        )
    input_ds.phenomenon_end_time = pd.Timestamp("2026-01-01T02:10:00Z")
    input_ds.save(update_fields=["phenomenon_end_time"])

    second_run = run_data_product_task(str(transformation.task_id))

    assert second_run["loaded_total"] == 1
    assert second_run["errors"] == {}
    incremental = list(Observation.objects.filter(datastream=output_ds).order_by(
        "phenomenon_time"
    ).values_list("phenomenon_time", "result"))
    # 01:00 boundary interpolates between 00:40=4 and 01:20=8 -> 6, and the
    # result matches aggregating the full history in one pass.
    full = apply_aggregation(
        _fetch_observations(input_ds),
        interval="1h",
        method="time_weighted_mean",
    )
    assert [t for t, _ in incremental] == [
        pd.Timestamp("2026-01-01T00:00:00Z"),
        pd.Timestamp("2026-01-01T01:00:00Z"),
    ]
    assert [r for _, r in incremental] == pytest.approx([3.0, 31 / 6])
    assert [r for _, r in incremental] == pytest.approx(full[RESULT_COL].tolist()[:2])


@pytest.mark.parametrize("transformation_type", ["derivation", "rating_curve"])
def test_pointwise_transformations_exclude_already_processed_observation(transformation_type):
    output_ds = DatastreamFactory(
        phenomenon_end_time=pd.Timestamp("2026-01-01T01:00:00Z")
    )
    input_ds = DatastreamFactory(
        monitoring_site=output_ds.monitoring_site,
        phenomenon_end_time=pd.Timestamp("2026-01-01T02:00:00Z"),
    )
    transformation = DataProductTransformationFactory(
        task__monitoring_site=output_ds.monitoring_site,
        output_datastream=output_ds,
        transformation_type=transformation_type,
        formula="x * 2" if transformation_type == "derivation" else None,
    )
    DataProductTransformationInputFactory(
        transformation=transformation, datastream=input_ds, variable_name="x"
    )
    if transformation_type == "rating_curve":
        curve = RatingCurveFactory(monitoring_site=output_ds.monitoring_site)
        RatingCurvePointFactory(rating_curve=curve, input_value=0, output_value=0)
        RatingCurvePointFactory(rating_curve=curve, input_value=100, output_value=200)
        transformation.rating_curve = curve
        transformation.save(update_fields=["rating_curve"])
    ObservationFactory(
        datastream=output_ds,
        phenomenon_time=pd.Timestamp("2026-01-01T01:00:00Z"),
        result=2.0,
    )
    for timestamp, value in [
        ("2026-01-01T01:00:00Z", 1.0),
        ("2026-01-01T02:00:00Z", 2.0),
    ]:
        ObservationFactory(
            datastream=input_ds, phenomenon_time=pd.Timestamp(timestamp), result=value
        )

    result = run_data_product_task(str(transformation.task_id))

    assert result["loaded_total"] == 1
    assert result["errors"] == {}
    assert list(Observation.objects.filter(datastream=output_ds).order_by(
        "phenomenon_time"
    ).values_list("phenomenon_time", "result")) == [
        (pd.Timestamp("2026-01-01T01:00:00Z"), 2.0),
        (pd.Timestamp("2026-01-01T02:00:00Z"), 4.0),
    ]


def test_load_to_datastream_writes_observations_tagged_with_the_output_datastream_id():
    transformation = DataProductTransformationFactory()
    result_df = pd.DataFrame({
        TIMESTAMP_COL: pd.to_datetime(
            ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"], utc=True
        ),
        RESULT_COL: [1.0, 2.0],
    })

    with patch("processing.products.tasks.observation_service") as mock_service:
        loaded = _load_to_datastream(transformation, result_df)

    assert loaded == 2
    mock_service.bulk_create.assert_called_once()
    call_kwargs = mock_service.bulk_create.call_args.kwargs
    assert call_kwargs["datastream_id"] == transformation.output_datastream.pk
    assert call_kwargs["data"].datastream_id == transformation.output_datastream.pk
    assert call_kwargs["data"].fields == ["phenomenonTime", "result"]
    assert list(call_kwargs["data"].data) == [
        [pd.Timestamp("2026-01-01T00:00:00", tz="UTC"), 1.0],
        [pd.Timestamp("2026-01-01T01:00:00", tz="UTC"), 2.0],
    ]
