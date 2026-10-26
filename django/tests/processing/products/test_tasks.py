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


def _hour(hour):
    return pd.Timestamp(f"2026-01-01T{hour:02d}:00:00Z")


def _append_obs(datastream, obs):
    """Add {hour: value} readings to a datastream and advance its end time."""
    for hour, value in obs.items():
        ObservationFactory(datastream=datastream, phenomenon_time=_hour(hour), result=value)
    datastream.phenomenon_end_time = _hour(max(obs))
    datastream.save(update_fields=["phenomenon_end_time"])


def _make_offset_derivation(obs_a, obs_b, **transformation_kwargs):
    """
    Create inputs ds_a/ds_b from {hour: value} dicts and an "a + b" derivation
    into an empty output. Returns (transformation, ds_a, ds_b, ds_out).
    """
    ds_out = DatastreamFactory()
    ds_a = DatastreamFactory(monitoring_site=ds_out.monitoring_site)
    ds_b = DatastreamFactory(monitoring_site=ds_out.monitoring_site)
    _append_obs(ds_a, obs_a)
    _append_obs(ds_b, obs_b)
    transformation = DataProductTransformationFactory(
        task__monitoring_site=ds_out.monitoring_site,
        output_datastream=ds_out,
        transformation_type="derivation",
        formula="a + b",
        **transformation_kwargs,
    )
    for ds, name in [(ds_a, "a"), (ds_b, "b")]:
        DataProductTransformationInputFactory(
            transformation=transformation, datastream=ds, variable_name=name
        )
    return transformation, ds_a, ds_b, ds_out


def _run(transformation):
    result = run_data_product_task(str(transformation.task_id))
    assert result["errors"] == {}
    return result["loaded_total"]


def _output_results(ds_out):
    return [
        (t.hour, r) for t, r in Observation.objects.filter(datastream=ds_out)
        .order_by("phenomenon_time")
        .values_list("phenomenon_time", "result")
    ]


def test_derivation_initial_load_starts_at_latest_input_start():
    """
    ds_a starts at 08:00, ds_b at 10:00, aligned from there. The initial load
    should start at 10:00 rather than stopping at ds_a's leading readings.
    """
    t, _, _, ds_out = _make_offset_derivation(
        obs_a={8: 1.0, 9: 2.0, 10: 3.0, 11: 4.0},
        obs_b={10: 10.0, 11: 20.0},
        stop_on_gaps=True,
    )
    assert _run(t) == 2
    assert _output_results(ds_out) == [(10, 13.0), (11, 24.0)]


def test_derivation_offset_start_then_incremental_run():
    """After an offset-start initial load, the next run appends normally."""
    t, ds_a, ds_b, ds_out = _make_offset_derivation(
        obs_a={8: 1.0, 9: 2.0, 10: 3.0},
        obs_b={9: 10.0, 10: 20.0},
    )
    assert _run(t) == 2

    _append_obs(ds_a, {11: 4.0, 12: 5.0})
    _append_obs(ds_b, {11: 49.0, 12: 50.0})
    assert _run(t) == 2
    assert _output_results(ds_out) == [(9, 12.0), (10, 23.0), (11, 53.0), (12, 55.0)]


def test_derivation_offset_start_stops_at_divergence():
    """Trimming to the latest start doesn't bypass divergence after that point."""
    t, _, _, ds_out = _make_offset_derivation(
        obs_a={8: 1.0, 10: 3.0, 11: 4.0, 12: 5.0},
        obs_b={10: 10.0, 12: 30.0},
        stop_on_gaps=True,
    )
    assert _run(t) == 1
    assert _output_results(ds_out) == [(10, 13.0)]


def test_derivation_stop_on_gaps_true_waits_at_gap():
    """With the toggle on, a gap holds the output back on every run until it's filled."""
    t, ds_a, ds_b, ds_out = _make_offset_derivation(
        obs_a={8: 1.0, 9: 2.0, 10: 3.0},
        obs_b={8: 10.0, 10: 30.0},
        stop_on_gaps=True,
    )
    assert _run(t) == 1

    _append_obs(ds_a, {11: 4.0})
    _append_obs(ds_b, {11: 40.0})
    assert _run(t) == 0

    ObservationFactory(datastream=ds_b, phenomenon_time=_hour(9), result=20.0)
    assert _run(t) == 3
    assert _output_results(ds_out) == [(8, 11.0), (9, 22.0), (10, 33.0), (11, 44.0)]


def test_derivation_skips_gaps_when_stop_on_gaps_false():
    """With the toggle off, timestamps not shared by both inputs are skipped."""
    t, ds_a, ds_b, ds_out = _make_offset_derivation(
        obs_a={8: 1.0, 9: 2.0, 10: 3.0, 11: 4.0},
        obs_b={8: 10.0, 10: 30.0, 11: 40.0},
        stop_on_gaps=False,
    )
    assert _run(t) == 3
    assert _output_results(ds_out) == [(8, 11.0), (10, 33.0), (11, 44.0)]

    # The incremental run picks up after the last output and skips new gaps too.
    _append_obs(ds_a, {13: 6.0, 14: 7.0})
    _append_obs(ds_b, {12: 50.0, 14: 70.0})
    assert _run(t) == 1
    assert _output_results(ds_out) == [(8, 11.0), (10, 33.0), (11, 44.0), (14, 77.0)]


def test_derivation_lagging_input_holds_output_back():
    """
    ds_a falls behind ds_b. Output stops at ds_a's last reading rather than
    skipping ds_b's newer readings, then catches up once ds_a reports again,
    skipping the hour ds_a never reported.
    """
    t, ds_a, _, ds_out = _make_offset_derivation(
        obs_a={8: 1.0, 9: 2.0},
        obs_b={8: 10.0, 9: 20.0, 10: 30.0, 11: 40.0},
        stop_on_gaps=False,
    )
    assert _run(t) == 2
    assert _output_results(ds_out) == [(8, 11.0), (9, 22.0)]

    _append_obs(ds_a, {11: 4.0})
    assert _run(t) == 1
    assert _output_results(ds_out) == [(8, 11.0), (9, 22.0), (11, 44.0)]


def test_derivation_no_data_values_fill_output_and_continue():
    """
    Each input is checked against its own no-data value, and those rows get the
    output's no-data value. The run continues with the toggle at its default (off).
    """
    # 09:00: ds_a at its no-data value. 10:00: ds_b at its no-data value.
    # 11:00: each holds the *other's* no-data value, which is real data.
    t, ds_a, ds_b, ds_out = _make_offset_derivation(
        obs_a=dict(zip((8, 9, 10, 11), (1.0, -9999.0, 3.0, -1.0))),
        obs_b=dict(zip((8, 9, 10, 11), (10.0, 20.0, -1.0, -9999.0))),
    )
    for ds, ndv in [(ds_a, -9999), (ds_b, -1), (ds_out, -555)]:
        ds.no_data_value = ndv
        ds.save(update_fields=["no_data_value"])

    assert t.stop_on_gaps is False
    assert _run(t) == 4
    assert _output_results(ds_out) == [(8, 11.0), (9, -555.0), (10, -555.0), (11, -10000.0)]


def test_derivation_latest_start_not_shared_loads_nothing():
    """
    ds_a starts at 02:00 and ds_b at 01:00, but ds_b has no 02:00 reading; the
    first shared timestamp is 03:00. The latest start doesn't align, so nothing loads.
    """
    t, _, _, ds_out = _make_offset_derivation(
        obs_a={2: 1.0, 3: 2.0},
        obs_b={1: 10.0, 3: 20.0},
        stop_on_gaps=True,
    )
    assert _run(t) == 0
    assert _output_results(ds_out) == []


def test_derivation_non_overlapping_inputs_load_nothing():
    """ds_b starts after ds_a's last reading, so there's nothing to derive yet."""
    t, _, _, ds_out = _make_offset_derivation(
        obs_a={8: 1.0, 9: 2.0},
        obs_b={10: 10.0, 11: 20.0},
    )
    assert _run(t) == 0
    assert _output_results(ds_out) == []
