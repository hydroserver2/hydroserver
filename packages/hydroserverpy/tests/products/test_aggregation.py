import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone

from hydroserverpy.products.aggregation import apply_aggregation
from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _utc(year, month, day, hour=0, minute=0, second=0):
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _make_df(timestamps, values):
    return pd.DataFrame({
        TIMESTAMP_COL: pd.DatetimeIndex(timestamps).as_unit("us"),
        RESULT_COL: np.array(list(values), dtype=np.float64),
    })


# 4 observations spread across Jan 1, with values [1, 3, 2, 4]
_JAN1_TS = [_utc(2024, 1, 1, 6), _utc(2024, 1, 1, 8), _utc(2024, 1, 1, 10), _utc(2024, 1, 1, 12)]
_JAN1_VALS = [1.0, 3.0, 2.0, 4.0]


def _jan1_df():
    return _make_df(_JAN1_TS, _JAN1_VALS)


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------

class TestApplyAggregationOutputStructure:

    def test_output_has_timestamp_and_result_columns(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="mean")
        assert TIMESTAMP_COL in result.columns
        assert RESULT_COL in result.columns

    def test_output_schema_matches_canonical(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="mean")
        assert pd.api.types.is_datetime64_any_dtype(result[TIMESTAMP_COL])
        assert pd.api.types.is_float_dtype(result[RESULT_COL])

    def test_four_observations_same_day_produce_one_row(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="mean")
        assert len(result) == 1

    def test_observations_on_two_days_produce_two_rows(self):
        ts = _JAN1_TS + [_utc(2024, 1, 2, 6), _utc(2024, 1, 2, 12)]
        df = _make_df(ts, _JAN1_VALS + [5.0, 6.0])
        result = apply_aggregation(df, interval="1d", method="mean")
        assert len(result) == 2

    def test_output_is_sorted_by_timestamp(self):
        ts = _JAN1_TS + [_utc(2024, 1, 2, 6), _utc(2024, 1, 2, 12)]
        df = _make_df(ts, _JAN1_VALS + [5.0, 6.0])
        result = apply_aggregation(df, interval="1d", method="mean")
        ts_sorted = result[TIMESTAMP_COL].sort_values()
        assert result[TIMESTAMP_COL].tolist() == ts_sorted.tolist()


# ---------------------------------------------------------------------------
# Aggregation methods
# ---------------------------------------------------------------------------

class TestApplyAggregationMethods:

    def test_min_returns_minimum_value_in_window(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="min")
        assert result[RESULT_COL].iloc[0] == pytest.approx(1.0)

    def test_max_returns_maximum_value_in_window(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="max")
        assert result[RESULT_COL].iloc[0] == pytest.approx(4.0)

    def test_sum_returns_sum_of_window_values(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="sum")
        assert result[RESULT_COL].iloc[0] == pytest.approx(10.0)

    def test_mean_returns_arithmetic_mean(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="mean")
        assert result[RESULT_COL].iloc[0] == pytest.approx(2.5)

    def test_first_returns_first_value_chronologically(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="first")
        assert result[RESULT_COL].iloc[0] == pytest.approx(1.0)

    def test_last_returns_last_value_chronologically(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="last")
        assert result[RESULT_COL].iloc[0] == pytest.approx(4.0)

    def test_hourly_interval_groups_sub_hour_observations(self):
        ts = [_utc(2024, 1, 1, 0, 10), _utc(2024, 1, 1, 0, 30), _utc(2024, 1, 1, 0, 50)]
        df = _make_df(ts, [1.0, 2.0, 3.0])
        result = apply_aggregation(df, interval="1h", method="mean")
        assert len(result) == 1
        assert result[RESULT_COL].iloc[0] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# time_weighted_mean (trapezoidal integration)
# ---------------------------------------------------------------------------

class TestApplyAggregationTimeWeightedMean:

    def test_constant_series_equals_constant(self):
        ts = [_utc(2024, 1, 1, 6), _utc(2024, 1, 1, 12), _utc(2024, 1, 1, 18)]
        df = _make_df(ts, [5.0, 5.0, 5.0])
        result = apply_aggregation(df, interval="1d", method="time_weighted_mean")
        assert result[RESULT_COL].iloc[0] == pytest.approx(5.0)

    def test_linear_series_equals_midpoint(self):
        # Hourly observations 0..23 plus the value at the next day's boundary (24)
        # trace a straight line, so the time-weighted mean over the day is the midpoint.
        ts = [_utc(2024, 1, 15, h) for h in range(24)] + [_utc(2024, 1, 16, 0)]
        vals = [float(h) for h in range(25)]
        df = _make_df(ts, vals)
        result = apply_aggregation(df, interval="1d", method="time_weighted_mean")
        assert result[RESULT_COL].iloc[0] == pytest.approx(12.0)

    def test_weights_longer_intervals_more_than_simple_mean(self):
        # A value held for most of the day should dominate the time-weighted mean,
        # unlike the simple arithmetic mean which treats every observation equally.
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 6), _utc(2024, 1, 1, 23)]
        df = _make_df(ts, [0.0, 12.0, 12.0])
        result = apply_aggregation(df, interval="1d", method="time_weighted_mean")
        simple = apply_aggregation(df, interval="1d", method="mean")
        assert result[RESULT_COL].iloc[0] == pytest.approx(10.5)
        assert result[RESULT_COL].iloc[0] != pytest.approx(simple[RESULT_COL].iloc[0])

    def test_extrapolates_flat_when_no_observation_before_window_start(self):
        # No observation before 06:00, so the window-start boundary is a flat
        # extrapolation of the first observation's value.
        ts = [_utc(2024, 1, 1, 6), _utc(2024, 1, 1, 18)]
        df = _make_df(ts, [10.0, 20.0])
        result = apply_aggregation(df, interval="1d", method="time_weighted_mean")
        # (10+10)/2*6h + (10+20)/2*12h + (20+20)/2*6h, over 24h
        expected = ((10 + 10) / 2 * 6 + (10 + 20) / 2 * 12 + (20 + 20) / 2 * 6) / 24
        assert result[RESULT_COL].iloc[0] == pytest.approx(expected)

    def test_single_observation_in_window_equals_that_value(self):
        ts = [_utc(2024, 1, 1, 12)]
        df = _make_df(ts, [7.0])
        result = apply_aggregation(df, interval="1d", method="time_weighted_mean")
        assert result[RESULT_COL].iloc[0] == pytest.approx(7.0)

    def test_dst_spring_forward_window_uses_actual_23_hour_duration(self):
        # 2024-03-10 is a 23-hour local day in America/Denver (spring forward).
        # A naive `window_start + timedelta(days=1)` would overshoot the true
        # boundary by an hour and skew the result.
        ts = [_utc(2024, 3, 10, 10), _utc(2024, 3, 10, 20)]
        df = _make_df(ts, [1.0, 2.0])
        result = apply_aggregation(
            df, interval="1d", method="time_weighted_mean", local_timezone="America/Denver"
        )
        assert result[RESULT_COL].iloc[0] == pytest.approx(136800 / 82800)

    def test_multiple_windows_computed_independently(self):
        ts = _JAN1_TS + [_utc(2024, 1, 2, 6), _utc(2024, 1, 2, 12), _utc(2024, 1, 2, 18)]
        df = _make_df(ts, _JAN1_VALS + [5.0, 6.0, 7.0])
        result = apply_aggregation(df, interval="1d", method="time_weighted_mean")
        assert len(result) == 2

    def test_respects_min_values_and_on_sparse(self):
        # Jan 1 has 4 obs (passes), Jan 2 has 1 obs (fails min_values=3)
        ts = _JAN1_TS + [_utc(2024, 1, 2, 6)]
        df = _make_df(ts, _JAN1_VALS + [5.0])
        result = apply_aggregation(
            df, interval="1d", method="time_weighted_mean", min_values=3, on_sparse="drop"
        )
        assert len(result) == 1


# ---------------------------------------------------------------------------
# min_values and on_sparse
# ---------------------------------------------------------------------------

class TestApplyAggregationSparseHandling:

    def _two_window_df(self):
        ts = _JAN1_TS + [_utc(2024, 1, 2, 6)]
        return _make_df(ts, _JAN1_VALS + [5.0])

    def test_min_values_less_than_one_raises(self):
        with pytest.raises(ValueError):
            apply_aggregation(_jan1_df(), interval="1d", method="mean", min_values=0)

    def test_on_sparse_without_min_values_is_ignored(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="mean", on_sparse="raise")
        assert len(result) == 1

    def test_on_sparse_drop_removes_windows_below_threshold(self):
        # Jan 1 has 4 obs (passes), Jan 2 has 1 obs (fails min_values=3)
        result = apply_aggregation(self._two_window_df(), interval="1d", method="mean", min_values=3)
        assert len(result) == 1

    def test_on_sparse_raise_raises_when_sparse_window_exists(self):
        with pytest.raises(ValueError):
            apply_aggregation(
                self._two_window_df(), interval="1d", method="mean", min_values=3, on_sparse="raise"
            )

    def test_on_sparse_raise_passes_when_all_windows_meet_threshold(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="mean", min_values=1, on_sparse="raise")
        assert len(result) == 1

    def test_on_sparse_stop_truncates_at_first_sparse_window(self):
        # Jan 1 passes, Jan 2 fails → output is Jan 1 only
        result = apply_aggregation(
            self._two_window_df(), interval="1d", method="mean", min_values=3, on_sparse="stop"
        )
        assert len(result) == 1

    def test_min_values_met_in_all_windows_returns_all_rows(self):
        ts = _JAN1_TS + [_utc(2024, 1, 2, 6), _utc(2024, 1, 2, 12), _utc(2024, 1, 2, 18)]
        df = _make_df(ts, _JAN1_VALS + [5.0, 6.0, 7.0])
        result = apply_aggregation(df, interval="1d", method="mean", min_values=3)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Timezone and anchor
# ---------------------------------------------------------------------------

class TestApplyAggregationTimezoneAndAnchor:

    def test_local_timezone_groups_cross_midnight_observations_by_local_day(self):
        # UTC 2024-01-01 12:00 = 2024-01-01 05:00 in Etc/GMT+7 (UTC-7) → local Jan 1
        # UTC 2024-01-02 01:00 = 2024-01-01 18:00 in Etc/GMT+7 (UTC-7) → local Jan 1
        ts = [_utc(2024, 1, 1, 12), _utc(2024, 1, 2, 1)]
        df = _make_df(ts, [1.0, 2.0])
        result = apply_aggregation(df, interval="1d", method="mean", local_timezone="Etc/GMT+7")
        assert len(result) == 1
        assert result[RESULT_COL].iloc[0] == pytest.approx(1.5)

    def test_anchor_shifts_window_boundary(self):
        # anchor at 00:30 → windows are 00:30–01:30, 01:30–02:30, ...
        anchor = _utc(2024, 1, 1, 0, 30)
        ts = [_utc(2024, 1, 1, 0, 45), _utc(2024, 1, 1, 1, 45)]
        df = _make_df(ts, [1.0, 2.0])
        result = apply_aggregation(df, interval="1h", method="mean", anchor=anchor)
        assert len(result) == 2
        first_ts = result.sort_values(TIMESTAMP_COL)[TIMESTAMP_COL].iloc[0]
        assert first_ts.minute == 30
        assert first_ts.hour == 0

# ---------------------------------------------------------------------------
# Whole-day (calendar) window grid
# ---------------------------------------------------------------------------

def _hourly_df(start, end, value=1.0):
    timestamps = pd.date_range(start, end, freq="1h", inclusive="left")
    return _make_df(timestamps, [value] * len(timestamps))


class TestApplyAggregationCalendarGrid:

    def test_weekly_windows_start_on_monday_by_default(self):
        # Data starts on Wednesday 2026-01-07; its window starts Monday 2026-01-05.
        df = _hourly_df(_utc(2026, 1, 7), _utc(2026, 1, 20))
        result = apply_aggregation(df, interval="1w", method="sum")
        assert result[TIMESTAMP_COL].tolist() == [
            pd.Timestamp("2026-01-05T00:00Z"), pd.Timestamp("2026-01-12T00:00Z"), pd.Timestamp("2026-01-19T00:00Z"),
        ]
        assert result[RESULT_COL].tolist() == [5 * 24, 7 * 24, 24]

    def test_weekly_windows_start_at_local_midnight_on_monday(self):
        df = _hourly_df(_utc(2026, 1, 7), _utc(2026, 1, 14))
        result = apply_aggregation(df, interval="1w", method="sum", local_timezone="America/Denver")
        assert result[TIMESTAMP_COL].iloc[0] == pd.Timestamp("2026-01-05T07:00Z")

    def test_anchor_sets_the_window_grid_date(self):
        # Anchored on Thursday 2026-01-01 (time of day ignored) → Thursday windows.
        df = _hourly_df(_utc(2026, 1, 5), _utc(2026, 1, 20))
        result = apply_aggregation(df, interval="1w", method="sum", anchor=_utc(2026, 1, 1, 15))
        assert result[TIMESTAMP_COL].tolist() == [
            pd.Timestamp("2026-01-01T00:00Z"), pd.Timestamp("2026-01-08T00:00Z"), pd.Timestamp("2026-01-15T00:00Z"),
        ]

    @pytest.mark.parametrize("interval", ["1d", "3d", "1w", "2w"])
    @pytest.mark.parametrize("local_timezone", [None, "America/Denver"])
    def test_windows_do_not_depend_on_where_input_starts(self, interval, local_timezone):
        # Spans the Mar 8 DST change in Denver.
        df = _hourly_df(_utc(2026, 1, 1), _utc(2026, 4, 1))
        kwargs = dict(interval=interval, method="sum", local_timezone=local_timezone)
        full = apply_aggregation(df, **kwargs)
        edge = full[TIMESTAMP_COL].iloc[len(full) // 2]

        # Splitting at a window edge and aggregating each part separately gives the
        # same windows as aggregating it all at once.
        parts = pd.concat([
            apply_aggregation(df[df[TIMESTAMP_COL] < edge], **kwargs),
            apply_aggregation(df[df[TIMESTAMP_COL] >= edge], **kwargs),
        ], ignore_index=True)
        pd.testing.assert_frame_equal(parts, full)

        # Input starting mid-window (e.g. after a gap) still lands on the same grid.
        mid_window = df[df[TIMESTAMP_COL] >= edge + pd.Timedelta(days=1, hours=5)]
        later = apply_aggregation(mid_window, **kwargs)
        assert set(later[TIMESTAMP_COL]) <= set(full[TIMESTAMP_COL])

    def test_data_starting_on_a_nonexistent_local_midnight(self):
        # America/Santiago springs forward at midnight: 2026-09-06 00:00 doesn't exist,
        # so that day runs 01:00 (-03) = 04:00Z → 2026-09-07 00:00 (-03) = 03:00Z (23h).
        df = _hourly_df(_utc(2026, 9, 6, 4), _utc(2026, 9, 7, 4))
        result = apply_aggregation(df, interval="1d", method="sum", local_timezone="America/Santiago")
        assert result[TIMESTAMP_COL].tolist() == [pd.Timestamp("2026-09-06T04:00Z"), pd.Timestamp("2026-09-07T03:00Z")]
        assert result[RESULT_COL].tolist() == [23.0, 1.0]

    def test_data_starting_on_an_ambiguous_local_midnight(self):
        # America/Havana falls back at 01:00 → 00:00 on 2026-11-01, so that day runs
        # from the first 00:00 (-04) = 04:00Z to 2026-11-02 00:00 (-05) = 05:00Z (25h).
        df = _hourly_df(_utc(2026, 11, 1, 4), _utc(2026, 11, 2, 6))
        result = apply_aggregation(df, interval="1d", method="sum", local_timezone="America/Havana")
        assert result[TIMESTAMP_COL].tolist() == [pd.Timestamp("2026-11-01T04:00Z"), pd.Timestamp("2026-11-02T05:00Z")]
        assert result[RESULT_COL].tolist() == [25.0, 1.0]

    def test_time_weighted_mean_window_ends_at_its_edge_when_next_window_is_empty(self):
        # Values rise 1 per hour from 0 (Jan 1 12:00) to 48 (Jan 3 12:00); Jan 2 has no data.
        # Jan 1: 0 until 12:00, then linear to 12 at midnight → (0*12 + 6*12) / 24 = 3.
        # Jan 3: 36 at midnight, linear to 48 at 12:00, then flat → (42*12 + 48*12) / 24 = 45.
        df = _make_df([_utc(2026, 1, 1, 12), _utc(2026, 1, 3, 12)], [0.0, 48.0])
        result = apply_aggregation(df, interval="1d", method="time_weighted_mean")
        assert result[TIMESTAMP_COL].tolist() == [pd.Timestamp("2026-01-01T00:00Z"), pd.Timestamp("2026-01-03T00:00Z")]
        assert result[RESULT_COL].tolist() == pytest.approx([3.0, 45.0])

    def test_empty_input_returns_empty_result(self):
        df = _make_df([], [])
        result = apply_aggregation(df, interval="1w", method="sum")
        assert len(result) == 0
        assert list(result.columns) == [TIMESTAMP_COL, RESULT_COL]
