import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from hydroserverpy.etl.operations.temporal_aggregation import TemporalAggregationOperation


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

UTC = timezone.utc


def _make_agg(**kwargs) -> TemporalAggregationOperation:
    defaults = dict(aggregation_statistic="simple_mean", target_identifier="1")
    defaults.update(kwargs)
    return TemporalAggregationOperation(**defaults)


def _utc(year, month, day, hour=0, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


def _make_tv_df(timestamps: list[datetime], values: list) -> pd.DataFrame:
    """Build a (timestamp, value) DataFrame with UTC timestamps."""
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps, utc=True),
        "value": pd.array(values, dtype=object),
    })


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

class TestTemporalAggregationModel:

    def test_aggregation_statistic_is_stored(self):
        agg = _make_agg(aggregation_statistic="simple_mean")
        assert agg.aggregation_statistic == "simple_mean"

    def test_aggregation_statistic_is_required(self):
        with pytest.raises(Exception):
            TemporalAggregation()  # noqa

    @pytest.mark.parametrize("statistic", [
        "simple_mean", "time_weighted_mean", "last_value_of_period",
    ])
    def test_valid_statistics_are_accepted(self, statistic):
        agg = _make_agg(aggregation_statistic=statistic)
        assert agg.aggregation_statistic == statistic

    def test_invalid_statistic_raises_error(self):
        with pytest.raises(Exception):
            _make_agg(aggregation_statistic="invalid_stat")

    def test_aggregation_interval_defaults_to_one(self):
        agg = _make_agg()
        assert agg.aggregation_interval == 1

    def test_aggregation_interval_unit_defaults_to_day(self):
        agg = _make_agg()
        assert agg.aggregation_interval_unit == "day"

    def test_timezone_type_defaults_to_none(self):
        agg = _make_agg()
        assert agg.timezone_type is None

    def test_utc_timezone_type_is_accepted(self):
        agg = _make_agg(timezone_type="utc")
        assert agg.timezone_type == "utc"

    def test_offset_timezone_type_requires_timezone(self):
        with pytest.raises(ValueError):
            _make_agg(timezone_type="offset")

    def test_iana_timezone_type_requires_timezone(self):
        with pytest.raises(ValueError):
            _make_agg(timezone_type="iana")

    def test_valid_offset_timezone_is_accepted(self):
        agg = _make_agg(timezone_type="offset", timezone="-0700")
        assert agg.timezone == "-0700"

    def test_valid_iana_timezone_is_accepted(self):
        agg = _make_agg(timezone_type="iana", timezone="America/Denver")
        assert agg.timezone == "America/Denver"

    def test_invalid_iana_timezone_raises_error(self):
        with pytest.raises(ValueError, match="Invalid IANA timezone"):
            _make_agg(timezone_type="iana", timezone="Not/ATimezone")

    def test_multi_day_interval_is_accepted(self):
        agg = _make_agg(aggregation_interval=3)
        assert agg.aggregation_interval == 3


# ---------------------------------------------------------------------------
# _effective_tz
# ---------------------------------------------------------------------------

class TestEffectiveTz:

    def test_none_timezone_type_returns_utc(self):
        agg = _make_agg()
        assert agg._effective_tz() == UTC

    def test_utc_timezone_type_returns_utc(self):
        agg = _make_agg(timezone_type="utc")
        assert agg._effective_tz() == UTC

    def test_offset_timezone_type_returns_fixed_offset(self):
        agg = _make_agg(timezone_type="offset", timezone="-0700")
        tz = agg._effective_tz()
        assert tz.utcoffset(None) == timedelta(hours=-7)

    def test_iana_timezone_type_returns_zone_info(self):
        agg = _make_agg(timezone_type="iana", timezone="America/Denver")
        assert agg._effective_tz() == ZoneInfo("America/Denver")


# ---------------------------------------------------------------------------
# _window_start
# ---------------------------------------------------------------------------

class TestWindowStart:

    def test_returns_local_midnight_for_utc(self):
        agg = _make_agg()
        ts = _utc(2024, 1, 15, 14, 30)
        result = agg._window_start(ts)
        assert result.date().year == 2024
        assert result.date().month == 1
        assert result.date().day == 15
        assert result.hour == 0 and result.minute == 0 and result.second == 0

    def test_midnight_timestamp_maps_to_same_day(self):
        agg = _make_agg()
        ts = _utc(2024, 1, 15, 0, 0, 0)
        result = agg._window_start(ts)
        assert result.date().day == 15

    def test_uses_local_date_for_offset_timezone(self):
        # UTC 2024-01-15 02:00 is 2024-01-14 19:00 in -0700
        agg = _make_agg(timezone_type="offset", timezone="-0700")
        ts = _utc(2024, 1, 15, 2, 0)
        result = agg._window_start(ts)
        assert result.date().day == 14

    def test_uses_local_date_for_iana_timezone(self):
        # UTC 2024-01-15 02:00 is 2024-01-14 21:00 in America/Denver (UTC-7 in Jan)
        agg = _make_agg(timezone_type="iana", timezone="America/Denver")
        ts = _utc(2024, 1, 15, 2, 0)
        result = agg._window_start(ts)
        assert result.date().day == 14


# ---------------------------------------------------------------------------
# _next_window_start
# ---------------------------------------------------------------------------

class TestNextWindowStart:

    def test_advances_by_one_day(self):
        agg = _make_agg()
        current = datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC)
        result = agg._next_window_start(current)
        assert result.date().day == 16

    def test_advances_by_multi_day_interval(self):
        agg = _make_agg(aggregation_interval=3)
        current = datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC)
        result = agg._next_window_start(current)
        assert result.date().day == 18

    def test_dst_spring_forward_produces_23_hour_day(self):
        # America/New_York springs forward 2024-03-10: clocks go from 02:00 to 03:00
        # so the day 2024-03-10 is only 23 hours long
        agg = _make_agg(timezone_type="iana", timezone="America/New_York")
        tz = ZoneInfo("America/New_York")
        current = datetime(2024, 3, 10, 0, 0, 0, tzinfo=tz)
        next_w = agg._next_window_start(current)
        span = (next_w.astimezone(UTC) - current.astimezone(UTC)).total_seconds()
        assert span == 23 * 3600

    def test_dst_fall_back_produces_25_hour_day(self):
        # America/New_York falls back 2024-11-03: clocks go from 02:00 back to 01:00
        # so the day 2024-11-03 is 25 hours long
        agg = _make_agg(timezone_type="iana", timezone="America/New_York")
        tz = ZoneInfo("America/New_York")
        current = datetime(2024, 11, 3, 0, 0, 0, tzinfo=tz)
        next_w = agg._next_window_start(current)
        span = (next_w.astimezone(UTC) - current.astimezone(UTC)).total_seconds()
        assert span == 25 * 3600


# ---------------------------------------------------------------------------
# _iter_windows
# ---------------------------------------------------------------------------

class TestIterWindows:

    def test_single_day_yields_one_window(self):
        agg = _make_agg()
        windows = list(agg._iter_windows(_utc(2024, 1, 15, 6), _utc(2024, 1, 16, 6)))
        assert len(windows) == 1

    def test_two_days_yields_two_windows(self):
        agg = _make_agg()
        windows = list(agg._iter_windows(_utc(2024, 1, 15, 6), _utc(2024, 1, 17, 6)))
        assert len(windows) == 2

    def test_window_starts_are_utc_aware(self):
        agg = _make_agg()
        windows = list(agg._iter_windows(_utc(2024, 1, 15, 6), _utc(2024, 1, 16, 6)))
        ws, we = windows[0]
        assert ws.tzinfo is not None
        assert we.tzinfo is not None

    def test_window_start_aligns_to_local_midnight(self):
        agg = _make_agg()
        windows = list(agg._iter_windows(_utc(2024, 1, 15, 6), _utc(2024, 1, 16, 6)))
        ws, _ = windows[0]
        assert ws == _utc(2024, 1, 15, 0, 0, 0)

    def test_window_end_is_next_midnight(self):
        agg = _make_agg()
        windows = list(agg._iter_windows(_utc(2024, 1, 15, 6), _utc(2024, 1, 16, 6)))
        _, we = windows[0]
        assert we == _utc(2024, 1, 16, 0, 0, 0)

    def test_windows_are_contiguous(self):
        agg = _make_agg()
        windows = list(agg._iter_windows(_utc(2024, 1, 15, 0), _utc(2024, 1, 17, 0)))
        assert windows[0][1] == windows[1][0]

    def test_observation_on_end_boundary_is_excluded(self):
        agg = _make_agg()
        windows = list(agg._iter_windows(_utc(2024, 1, 15, 0), _utc(2024, 1, 16, 0)))
        assert len(windows) == 1

    def test_offset_timezone_shifts_window_boundaries(self):
        agg = _make_agg(timezone_type="offset", timezone="-0700")
        windows = list(agg._iter_windows(_utc(2024, 1, 15, 8), _utc(2024, 1, 16, 8)))
        ws, we = windows[0]
        assert ws == _utc(2024, 1, 15, 7, 0, 0)
        assert we == _utc(2024, 1, 16, 7, 0, 0)

    def test_multi_day_interval_yields_wider_windows(self):
        agg = _make_agg(aggregation_interval=3)
        windows = list(agg._iter_windows(_utc(2024, 1, 1, 0), _utc(2024, 1, 4, 6)))
        assert len(windows) == 1
        ws, we = windows[0]
        assert (we - ws).days == 3

    def test_start_same_day_as_end_yields_no_windows(self):
        agg = _make_agg()
        windows = list(agg._iter_windows(_utc(2024, 1, 15, 6), _utc(2024, 1, 15, 8)))
        assert len(windows) == 0


# ---------------------------------------------------------------------------
# _boundary_value
# ---------------------------------------------------------------------------

class TestBoundaryValue:

    def _ts(self, hour) -> datetime:
        return _utc(2024, 1, 15, hour)

    def test_returns_exact_value_when_prev_matches_target(self):
        ts = [self._ts(6), self._ts(12), self._ts(18)]
        vs = [1.0, 2.0, 3.0]
        result = TemporalAggregationOperation._boundary_value(self._ts(6), ts, vs, 0, 1)
        assert result == 1.0

    def test_returns_exact_value_when_next_matches_target(self):
        ts = [self._ts(6), self._ts(12), self._ts(18)]
        vs = [1.0, 2.0, 3.0]
        result = TemporalAggregationOperation._boundary_value(self._ts(12), ts, vs, 0, 1)
        assert result == 2.0

    def test_interpolates_between_prev_and_next(self):
        ts = [self._ts(0), self._ts(12)]
        vs = [0.0, 12.0]
        result = TemporalAggregationOperation._boundary_value(self._ts(6), ts, vs, 0, 1)
        assert result == pytest.approx(6.0)

    def test_extrapolates_from_prev_only(self):
        ts = [self._ts(6)]
        vs = [5.0]
        result = TemporalAggregationOperation._boundary_value(self._ts(12), ts, vs, 0, None)
        assert result == 5.0

    def test_extrapolates_from_next_only(self):
        ts = [self._ts(12)]
        vs = [7.0]
        result = TemporalAggregationOperation._boundary_value(self._ts(6), ts, vs, None, 0)
        assert result == 7.0

    def test_returns_none_when_no_observations(self):
        result = TemporalAggregationOperation._boundary_value(self._ts(6), [], [], None, None)
        assert result is None

    def test_returns_none_for_out_of_range_indices(self):
        ts = [self._ts(6)]
        vs = [1.0]
        result = TemporalAggregationOperation._boundary_value(self._ts(0), ts, vs, None, 99)
        assert result is None

    def test_zero_value_is_not_treated_as_missing(self):
        ts = [self._ts(6), self._ts(12)]
        vs = [0.0, 10.0]
        result = TemporalAggregationOperation._boundary_value(self._ts(6), ts, vs, 0, 1)
        assert result == pytest.approx(0.0)

    def test_zero_span_returns_next_value(self):
        ts = [self._ts(6), self._ts(6)]
        vs = [1.0, 5.0]
        result = TemporalAggregationOperation._boundary_value(self._ts(3), ts, vs, 0, 1)
        assert result == 5.0


# ---------------------------------------------------------------------------
# _aggregate_window
# ---------------------------------------------------------------------------

class TestAggregateWindow:

    def _make_agg(self, statistic):
        return _make_agg(aggregation_statistic=statistic)

    def _ts(self, hour) -> datetime:
        return _utc(2024, 1, 15, hour)

    def _window(self):
        return _utc(2024, 1, 15, 0), _utc(2024, 1, 16, 0)

    def test_returns_none_for_empty_timestamps(self):
        agg = self._make_agg("simple_mean")
        assert agg._aggregate_window([], [], *self._window()) is None

    def test_returns_none_when_window_end_before_start(self):
        agg = self._make_agg("simple_mean")
        ts = [self._ts(6)]
        result = agg._aggregate_window(ts, [1.0], self._ts(12), self._ts(6))
        assert result is None

    def test_returns_none_when_no_observations_in_window(self):
        agg = self._make_agg("simple_mean")
        ts = [self._ts(6)]
        result = agg._aggregate_window(ts, [1.0], self._ts(8), self._ts(10))
        assert result is None

    def test_simple_mean_single_observation(self):
        agg = self._make_agg("simple_mean")
        ts = [self._ts(6)]
        result = agg._aggregate_window(ts, [5.0], *self._window())
        assert result == pytest.approx(5.0)

    def test_simple_mean_multiple_observations(self):
        agg = self._make_agg("simple_mean")
        ts = [self._ts(6), self._ts(12), self._ts(18)]
        result = agg._aggregate_window(ts, [1.0, 2.0, 3.0], *self._window())
        assert result == pytest.approx(2.0)

    def test_simple_mean_excludes_observation_on_window_end(self):
        agg = self._make_agg("simple_mean")
        ts = [self._ts(6), _utc(2024, 1, 16, 0)]
        result = agg._aggregate_window(ts, [2.0, 999.0], *self._window())
        assert result == pytest.approx(2.0)

    def test_last_value_of_period_returns_last_in_window(self):
        agg = self._make_agg("last_value_of_period")
        ts = [self._ts(6), self._ts(12), self._ts(18)]
        result = agg._aggregate_window(ts, [1.0, 2.0, 3.0], *self._window())
        assert result == pytest.approx(3.0)

    def test_last_value_of_period_single_observation(self):
        agg = self._make_agg("last_value_of_period")
        ts = [self._ts(12)]
        result = agg._aggregate_window(ts, [7.0], *self._window())
        assert result == pytest.approx(7.0)

    def test_time_weighted_mean_constant_series_equals_constant(self):
        agg = self._make_agg("time_weighted_mean")
        ts = [self._ts(6), self._ts(12), self._ts(18)]
        result = agg._aggregate_window(ts, [5.0, 5.0, 5.0], *self._window())
        assert result == pytest.approx(5.0)

    def test_time_weighted_mean_linear_series(self):
        agg = self._make_agg("time_weighted_mean")
        ws = _utc(2024, 1, 15, 0)
        we = _utc(2024, 1, 16, 0)
        ts = [_utc(2024, 1, 15, h) for h in range(24)] + [_utc(2024, 1, 16, 0)]
        vs = [float(h) for h in range(25)]
        result = agg._aggregate_window(ts, vs, ws, we)
        assert result == pytest.approx(12.0)

    def test_time_weighted_mean_weights_longer_intervals_more(self):
        agg = self._make_agg("time_weighted_mean")
        ts = [self._ts(0), self._ts(6), self._ts(23)]
        vs = [0.0, 12.0, 12.0]
        ws, we = self._window()
        result = agg._aggregate_window(ts, vs, ws, we)
        assert result == pytest.approx(10.5)

    def test_time_weighted_mean_returns_none_when_boundary_indeterminate(self):
        agg = self._make_agg("time_weighted_mean")
        ts = [self._ts(12)]
        result = agg._aggregate_window(ts, [5.0], self._ts(6), self._ts(18))
        assert result is not None


# ---------------------------------------------------------------------------
# apply – output structure
# ---------------------------------------------------------------------------

class TestApplyOutputStructure:

    def test_returns_dataframe(self):
        agg = _make_agg()
        df = _make_tv_df([_utc(2024, 1, 15, 12), _utc(2024, 1, 16, 12)], [1.0, 2.0])
        assert isinstance(agg.apply(df), pd.DataFrame)

    def test_result_has_timestamp_and_value_columns(self):
        agg = _make_agg()
        df = _make_tv_df([_utc(2024, 1, 15, 12), _utc(2024, 1, 16, 12)], [1.0, 2.0])
        result = agg.apply(df)
        assert set(result.columns) == {"timestamp", "value"}

    def test_timestamp_column_is_utc_aware(self):
        agg = _make_agg()
        df = _make_tv_df([_utc(2024, 1, 15, 12), _utc(2024, 1, 16, 12)], [1.0, 2.0])
        result = agg.apply(df)
        assert result["timestamp"].dt.tz == timezone.utc

    def test_timestamp_is_window_start_not_observation_time(self):
        agg = _make_agg()
        df = _make_tv_df([_utc(2024, 1, 15, 12), _utc(2024, 1, 16, 12)], [1.0, 2.0])
        result = agg.apply(df)
        assert result["timestamp"].iloc[0] == pd.Timestamp("2024-01-15 00:00:00", tz="UTC")

    def test_empty_dataframe_returns_empty_with_correct_columns(self):
        agg = _make_agg()
        result = agg.apply(_make_tv_df([], []))
        assert result.empty
        assert set(result.columns) == {"timestamp", "value"}

    def test_multiple_observations_same_day_produce_one_row(self):
        agg = _make_agg()
        df = _make_tv_df(
            [_utc(2024, 1, 15, 6), _utc(2024, 1, 15, 12), _utc(2024, 1, 15, 18), _utc(2024, 1, 16, 6)],
            [1.0, 2.0, 3.0, 4.0],
        )
        result = agg.apply(df)
        assert len(result) == 1
        assert result["value"].iloc[0] == pytest.approx(2.0)

    def test_observations_on_two_days_produce_two_rows(self):
        agg = _make_agg()
        df = _make_tv_df(
            [_utc(2024, 1, 15, 12), _utc(2024, 1, 16, 12), _utc(2024, 1, 17, 12)],
            [1.0, 2.0, 3.0],
        )
        result = agg.apply(df)
        assert len(result) == 2

    def test_day_with_no_observations_is_dropped(self):
        agg = _make_agg()
        df = _make_tv_df(
            [_utc(2024, 1, 15, 12), _utc(2024, 1, 17, 12), _utc(2024, 1, 18, 12)],
            [1.0, 2.0, 3.0],
        )
        result = agg.apply(df)
        assert len(result) == 2
        assert pd.Timestamp("2024-01-16 00:00:00", tz="UTC") not in result["timestamp"].values

    def test_non_numeric_values_coerced_to_nan(self):
        agg = _make_agg()
        df = _make_tv_df(
            [_utc(2024, 1, 15, 12), _utc(2024, 1, 16, 12)],
            ["not_a_number", "also_not_a_number"],
        )
        result = agg.apply(df)
        assert len(result) == 1
        assert pd.isna(result["value"].iloc[0])


# ---------------------------------------------------------------------------
# apply – statistics
# ---------------------------------------------------------------------------

class TestApplyStatistics:

    def test_simple_mean_across_full_day(self):
        agg = _make_agg(aggregation_statistic="simple_mean")
        df = _make_tv_df(
            [_utc(2024, 1, 15, 6), _utc(2024, 1, 15, 12), _utc(2024, 1, 15, 18), _utc(2024, 1, 16, 6)],
            [1.0, 2.0, 3.0, 4.0],
        )
        result = agg.apply(df)
        assert result["value"].iloc[0] == pytest.approx(2.0)

    def test_last_value_of_period_across_full_day(self):
        agg = _make_agg(aggregation_statistic="last_value_of_period")
        df = _make_tv_df(
            [_utc(2024, 1, 15, 6), _utc(2024, 1, 15, 12), _utc(2024, 1, 15, 18), _utc(2024, 1, 16, 6)],
            [1.0, 2.0, 3.0, 4.0],
        )
        result = agg.apply(df)
        assert result["value"].iloc[0] == pytest.approx(3.0)

    def test_time_weighted_mean_constant_equals_constant(self):
        agg = _make_agg(aggregation_statistic="time_weighted_mean")
        df = _make_tv_df(
            [_utc(2024, 1, 15, 0), _utc(2024, 1, 15, 12), _utc(2024, 1, 16, 0)],
            [5.0, 5.0, 5.0],
        )
        result = agg.apply(df)
        assert result["value"].iloc[0] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# apply – timezone behaviour
# ---------------------------------------------------------------------------

class TestApplyTimezone:

    def test_utc_timezone_aligns_windows_to_utc_midnight(self):
        agg = _make_agg(timezone_type="utc")
        df = _make_tv_df([_utc(2024, 1, 15, 12), _utc(2024, 1, 16, 12)], [1.0, 2.0])
        result = agg.apply(df)
        assert result["timestamp"].iloc[0] == pd.Timestamp("2024-01-15 00:00:00", tz="UTC")

    def test_offset_timezone_shifts_window_start(self):
        agg = _make_agg(timezone_type="offset", timezone="-0700")
        df = _make_tv_df([_utc(2024, 1, 15, 10), _utc(2024, 1, 16, 10)], [1.0, 2.0])
        result = agg.apply(df)
        assert result["timestamp"].iloc[0] == pd.Timestamp("2024-01-15 07:00:00", tz="UTC")

    def test_iana_timezone_shifts_window_start(self):
        agg = _make_agg(timezone_type="iana", timezone="America/Denver")
        df = _make_tv_df([_utc(2024, 1, 15, 10), _utc(2024, 1, 16, 10)], [1.0, 2.0])
        result = agg.apply(df)
        assert result["timestamp"].iloc[0] == pd.Timestamp("2024-01-15 07:00:00", tz="UTC")

    def test_observation_near_midnight_assigned_to_correct_local_day(self):
        agg = _make_agg(timezone_type="offset", timezone="-0700")
        df = _make_tv_df(
            [_utc(2024, 1, 15, 1), _utc(2024, 1, 15, 10), _utc(2024, 1, 16, 10)],
            [1.0, 2.0, 3.0],
        )
        result = agg.apply(df)
        assert len(result) == 2
        assert result["timestamp"].iloc[0] == pd.Timestamp("2024-01-14 07:00:00", tz="UTC")
        assert result["timestamp"].iloc[1] == pd.Timestamp("2024-01-15 07:00:00", tz="UTC")

    def test_dst_transition_day_handled_correctly(self):
        agg = _make_agg(timezone_type="iana", timezone="America/New_York")
        df = _make_tv_df([_utc(2024, 3, 10, 12), _utc(2024, 3, 11, 12)], [1.0, 2.0])
        result = agg.apply(df)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# apply – multi-day interval
# ---------------------------------------------------------------------------

class TestApplyMultiDayInterval:

    def test_three_day_interval_groups_three_days_into_one_row(self):
        agg = _make_agg(aggregation_interval=3)
        df = _make_tv_df(
            [_utc(2024, 1, 1, 12), _utc(2024, 1, 2, 12), _utc(2024, 1, 3, 12)],
            [1.0, 2.0, 3.0],
        )
        result = agg.apply(df)
        assert len(result) == 1
        assert result["value"].iloc[0] == pytest.approx(2.0)

    def test_three_day_interval_window_spans_correct_duration(self):
        agg = _make_agg(aggregation_interval=3)
        df = _make_tv_df(
            [_utc(2024, 1, 1, 12), _utc(2024, 1, 4, 12), _utc(2024, 1, 7, 12)],
            [1.0, 2.0, 3.0],
        )
        result = agg.apply(df)
        assert len(result) == 2
        span = (result["timestamp"].iloc[1] - result["timestamp"].iloc[0]).total_seconds()
        assert span == 3 * 24 * 3600
