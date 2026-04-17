import polars as pl
import pytest
from datetime import datetime, timezone

from hydroserverpy.products.aggregation import apply_aggregation
from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, SCHEMA


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _utc(year, month, day, hour=0, minute=0, second=0):
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _make_df(timestamps, values):
    us = [int(t.timestamp() * 1_000_000) for t in timestamps]
    return pl.DataFrame({
        TIMESTAMP_COL: pl.Series(us, dtype=pl.Int64).cast(pl.Datetime("us", "UTC")),
        RESULT_COL: pl.Series(list(values), dtype=pl.Float64),
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
        assert TIMESTAMP_COL in result.schema
        assert RESULT_COL in result.schema

    def test_output_schema_matches_canonical(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="mean")
        assert result.schema[TIMESTAMP_COL] == SCHEMA[TIMESTAMP_COL]
        assert result.schema[RESULT_COL] == SCHEMA[RESULT_COL]

    def test_four_observations_same_day_produce_one_row(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="mean")
        assert result.height == 1

    def test_observations_on_two_days_produce_two_rows(self):
        ts = _JAN1_TS + [_utc(2024, 1, 2, 6), _utc(2024, 1, 2, 12)]
        df = _make_df(ts, _JAN1_VALS + [5.0, 6.0])
        result = apply_aggregation(df, interval="1d", method="mean")
        assert result.height == 2

    def test_output_is_sorted_by_timestamp(self):
        ts = _JAN1_TS + [_utc(2024, 1, 2, 6), _utc(2024, 1, 2, 12)]
        df = _make_df(ts, _JAN1_VALS + [5.0, 6.0])
        result = apply_aggregation(df, interval="1d", method="mean")
        ts_sorted = result[TIMESTAMP_COL].sort()
        assert result[TIMESTAMP_COL].to_list() == ts_sorted.to_list()


# ---------------------------------------------------------------------------
# Aggregation methods
# ---------------------------------------------------------------------------

class TestApplyAggregationMethods:

    def test_min_returns_minimum_value_in_window(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="min")
        assert result[RESULT_COL][0] == pytest.approx(1.0)

    def test_max_returns_maximum_value_in_window(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="max")
        assert result[RESULT_COL][0] == pytest.approx(4.0)

    def test_sum_returns_sum_of_window_values(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="sum")
        assert result[RESULT_COL][0] == pytest.approx(10.0)

    def test_mean_returns_arithmetic_mean(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="mean")
        assert result[RESULT_COL][0] == pytest.approx(2.5)

    def test_first_returns_first_value_chronologically(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="first")
        assert result[RESULT_COL][0] == pytest.approx(1.0)

    def test_last_returns_last_value_chronologically(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="last")
        assert result[RESULT_COL][0] == pytest.approx(4.0)

    def test_hourly_interval_groups_sub_hour_observations(self):
        ts = [_utc(2024, 1, 1, 0, 10), _utc(2024, 1, 1, 0, 30), _utc(2024, 1, 1, 0, 50)]
        df = _make_df(ts, [1.0, 2.0, 3.0])
        result = apply_aggregation(df, interval="1h", method="mean")
        assert result.height == 1
        assert result[RESULT_COL][0] == pytest.approx(2.0)


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

    def test_on_sparse_without_min_values_raises(self):
        with pytest.raises(ValueError):
            apply_aggregation(_jan1_df(), interval="1d", method="mean", on_sparse="raise")

    def test_on_sparse_drop_removes_windows_below_threshold(self):
        # Jan 1 has 4 obs (passes), Jan 2 has 1 obs (fails min_values=3)
        result = apply_aggregation(self._two_window_df(), interval="1d", method="mean", min_values=3)
        assert result.height == 1

    def test_on_sparse_raise_raises_when_sparse_window_exists(self):
        with pytest.raises(ValueError):
            apply_aggregation(
                self._two_window_df(), interval="1d", method="mean", min_values=3, on_sparse="raise"
            )

    def test_on_sparse_raise_passes_when_all_windows_meet_threshold(self):
        result = apply_aggregation(_jan1_df(), interval="1d", method="mean", min_values=1, on_sparse="raise")
        assert result.height == 1

    def test_on_sparse_stop_truncates_at_first_sparse_window(self):
        # Jan 1 passes, Jan 2 fails → output is Jan 1 only
        result = apply_aggregation(
            self._two_window_df(), interval="1d", method="mean", min_values=3, on_sparse="stop"
        )
        assert result.height == 1

    def test_min_values_met_in_all_windows_returns_all_rows(self):
        ts = _JAN1_TS + [_utc(2024, 1, 2, 6), _utc(2024, 1, 2, 12), _utc(2024, 1, 2, 18)]
        df = _make_df(ts, _JAN1_VALS + [5.0, 6.0, 7.0])
        result = apply_aggregation(df, interval="1d", method="mean", min_values=3)
        assert result.height == 2


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
        assert result.height == 1
        assert result[RESULT_COL][0] == pytest.approx(1.5)

    def test_anchor_shifts_window_boundary(self):
        # anchor at 00:30 → windows are 00:30–01:30, 01:30–02:30, ...
        anchor = _utc(2024, 1, 1, 0, 30)
        ts = [_utc(2024, 1, 1, 0, 45), _utc(2024, 1, 1, 1, 45)]
        df = _make_df(ts, [1.0, 2.0])
        result = apply_aggregation(df, interval="1h", method="mean", anchor=anchor)
        assert result.height == 2
        first_ts = result.sort(TIMESTAMP_COL)[TIMESTAMP_COL][0]
        assert first_ts.minute == 30
        assert first_ts.hour == 0
