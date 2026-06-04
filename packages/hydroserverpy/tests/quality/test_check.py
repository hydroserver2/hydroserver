import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone

from hydroserverpy.quality.check import check_range, check_rate_of_change, check_persistence
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


def _hourly(values, start_hour=0):
    ts = [_utc(2024, 1, 1, start_hour + i) for i in range(len(values))]
    return _make_df(ts, values)


def _empty_df():
    return pd.DataFrame({
        TIMESTAMP_COL: pd.Series([], dtype="datetime64[us, UTC]"),
        RESULT_COL: pd.Series([], dtype=np.float64),
    })


# ---------------------------------------------------------------------------
# check_range
# ---------------------------------------------------------------------------

class TestCheckRangeValidation:

    def test_no_bounds_raises(self):
        with pytest.raises(ValueError, match="At least one"):
            check_range(_hourly([1.0, 2.0]), min_value=None, max_value=None)

    def test_min_greater_than_max_raises(self):
        with pytest.raises(ValueError, match="min_value must be less than max_value"):
            check_range(_hourly([1.0, 2.0]), min_value=5.0, max_value=1.0)

    def test_min_equal_to_max_raises(self):
        with pytest.raises(ValueError, match="min_value must be less than max_value"):
            check_range(_hourly([1.0, 2.0]), min_value=3.0, max_value=3.0)


class TestCheckRangeOutputStructure:

    def test_returns_dict_with_expected_keys(self):
        result = check_range(_hourly([1.0, 2.0, 3.0]), min_value=0.0, max_value=5.0)
        assert "violation_count" in result
        assert "timestamps" in result
        assert "values" in result

    def test_no_violations_returns_empty_lists(self):
        result = check_range(_hourly([1.0, 2.0, 3.0]), min_value=0.0, max_value=5.0)
        assert result["violation_count"] == 0
        assert result["timestamps"] == []
        assert result["values"] == []

    def test_empty_dataframe_returns_zero_violations(self):
        result = check_range(_empty_df(), min_value=0.0, max_value=10.0)
        assert result["violation_count"] == 0


class TestCheckRangeMinBound:

    def test_value_below_min_is_flagged(self):
        result = check_range(_hourly([-1.0, 2.0, 3.0]), min_value=0.0)
        assert result["violation_count"] == 1

    def test_value_at_min_is_not_flagged(self):
        result = check_range(_hourly([0.0, 2.0, 3.0]), min_value=0.0)
        assert result["violation_count"] == 0

    def test_multiple_values_below_min_all_flagged(self):
        result = check_range(_hourly([-2.0, -1.0, 1.0]), min_value=0.0)
        assert result["violation_count"] == 2

    def test_all_values_below_min_all_flagged(self):
        result = check_range(_hourly([-3.0, -2.0, -1.0]), min_value=0.0)
        assert result["violation_count"] == 3


class TestCheckRangeMaxBound:

    def test_value_above_max_is_flagged(self):
        result = check_range(_hourly([1.0, 2.0, 11.0]), max_value=10.0)
        assert result["violation_count"] == 1

    def test_value_at_max_is_not_flagged(self):
        result = check_range(_hourly([1.0, 2.0, 10.0]), max_value=10.0)
        assert result["violation_count"] == 0

    def test_multiple_values_above_max_all_flagged(self):
        result = check_range(_hourly([1.0, 11.0, 12.0]), max_value=10.0)
        assert result["violation_count"] == 2


class TestCheckRangeBothBounds:

    def test_value_within_range_not_flagged(self):
        result = check_range(_hourly([5.0]), min_value=0.0, max_value=10.0)
        assert result["violation_count"] == 0

    def test_value_outside_both_bounds_flagged(self):
        result = check_range(_hourly([-1.0, 5.0, 11.0]), min_value=0.0, max_value=10.0)
        assert result["violation_count"] == 2

    def test_violation_timestamps_match_flagged_observations(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 1), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [-1.0, 5.0, 11.0])
        result = check_range(df, min_value=0.0, max_value=10.0)
        assert len(result["timestamps"]) == 2

    def test_violation_values_match_flagged_observations(self):
        result = check_range(_hourly([-1.0, 5.0, 11.0]), min_value=0.0, max_value=10.0)
        assert sorted(result["values"]) == pytest.approx([-1.0, 11.0])


class TestCheckRangeNoDataValue:

    def test_no_data_value_excluded_from_check(self):
        result = check_range(_hourly([-9999.0, 5.0, 6.0]), min_value=0.0, max_value=10.0, no_data_value=-9999.0)
        assert result["violation_count"] == 0

    def test_without_no_data_value_sentinel_is_flagged(self):
        result = check_range(_hourly([-9999.0, 5.0, 6.0]), min_value=0.0, max_value=10.0)
        assert result["violation_count"] == 1

    def test_no_data_value_none_does_not_filter(self):
        result = check_range(_hourly([-1.0, 5.0]), min_value=0.0, max_value=10.0, no_data_value=None)
        assert result["violation_count"] == 1


# ---------------------------------------------------------------------------
# check_rate_of_change
# ---------------------------------------------------------------------------

class TestCheckRateOfChangeOutputStructure:

    def test_returns_dict_with_expected_keys(self):
        result = check_rate_of_change(_hourly([1.0, 2.0, 3.0]), window="1h", max_change=5.0)
        assert "violation_count" in result
        assert "timestamps" in result
        assert "changes" in result

    def test_empty_dataframe_returns_zero_violations(self):
        result = check_rate_of_change(_empty_df(), window="1h", max_change=5.0)
        assert result["violation_count"] == 0

    def test_single_observation_returns_zero_violations(self):
        result = check_rate_of_change(_hourly([1.0]), window="1h", max_change=5.0)
        assert result["violation_count"] == 0


class TestCheckRateOfChangeWindow:

    def test_observations_within_first_window_are_skipped(self):
        # 3 hourly observations with window=1h: obs at T=0 is ref only, obs at T=1h is first eligible
        result = check_rate_of_change(_hourly([1.0, 2.0, 3.0]), window="1h", max_change=0.5)
        # T=1h change=1.0 > 0.5, T=2h change=1.0 > 0.5 → 2 violations
        assert result["violation_count"] == 2

    def test_small_changes_within_tolerance_not_flagged(self):
        result = check_rate_of_change(_hourly([1.0, 1.1, 1.2]), window="1h", max_change=0.5)
        assert result["violation_count"] == 0

    def test_spike_at_single_point_flagged(self):
        result = check_rate_of_change(_hourly([1.0, 100.0, 1.0]), window="1h", max_change=5.0)
        assert result["violation_count"] == 2

    def test_change_exactly_at_max_not_flagged(self):
        result = check_rate_of_change(_hourly([0.0, 5.0]), window="1h", max_change=5.0)
        assert result["violation_count"] == 0

    def test_change_just_above_max_flagged(self):
        result = check_rate_of_change(_hourly([0.0, 5.001]), window="1h", max_change=5.0)
        assert result["violation_count"] == 1

    def test_negative_change_uses_absolute_value(self):
        result = check_rate_of_change(_hourly([10.0, 3.0]), window="1h", max_change=5.0)
        assert result["violation_count"] == 1

    def test_violation_timestamps_correspond_to_flagged_points(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 1), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [1.0, 100.0, 1.0])
        result = check_rate_of_change(df, window="1h", max_change=5.0)
        assert len(result["timestamps"]) == 2
        assert ts[1] in result["timestamps"] or result["timestamps"][0] == ts[1]

    def test_wider_window_compares_against_earlier_reference(self):
        # T=0: 1.0, T=1h: 2.0, T=2h: 10.0 — with 2h window, T=2h compares to T=0
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 1), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [1.0, 2.0, 10.0])
        result = check_rate_of_change(df, window="2h", max_change=5.0)
        # T=2h eligible, change from T=0 (1.0) to T=2h (10.0) = 9.0 > 5.0
        assert result["violation_count"] == 1


class TestCheckRateOfChangeGapHandling:

    def test_observation_after_gap_compared_to_pre_gap_reference(self):
        # T=0: 1.0, then gap, T=5h: 100.0 — with window=1h, T=5h lookback=T=4h,
        # asof join finds T=0 as most recent ref; change=99>5 → flagged
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 5)]
        df = _make_df(ts, [1.0, 100.0])
        result = check_rate_of_change(df, window="1h", max_change=5.0)
        assert result["violation_count"] == 1


class TestCheckRateOfChangeNoDataValue:

    def test_no_data_value_excluded_before_check(self):
        # NDV at T=1h; T=2h compares against T=0, change = 1.0 ≤ 5.0
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 1), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [1.0, -9999.0, 2.0])
        result = check_rate_of_change(df, window="1h", max_change=5.0, no_data_value=-9999.0)
        assert result["violation_count"] == 0

    def test_without_no_data_value_sentinel_treated_as_spike(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 1)]
        df = _make_df(ts, [1.0, -9999.0])
        result = check_rate_of_change(df, window="1h", max_change=5.0)
        assert result["violation_count"] == 1


# ---------------------------------------------------------------------------
# check_persistence
# ---------------------------------------------------------------------------

class TestCheckPersistenceOutputStructure:

    def test_returns_dict_with_expected_keys(self):
        result = check_persistence(_hourly([1.0, 1.0, 1.0]), window="1h")
        assert "violation_count" in result
        assert "timestamps" in result
        assert "values" in result

    def test_empty_dataframe_returns_zero_violations(self):
        result = check_persistence(_empty_df(), window="1h")
        assert result["violation_count"] == 0

    def test_single_observation_returns_zero_violations(self):
        result = check_persistence(_hourly([5.0]), window="1h")
        assert result["violation_count"] == 0


class TestCheckPersistenceWindow:

    def test_changing_values_not_flagged(self):
        result = check_persistence(_hourly([1.0, 2.0, 3.0, 4.0]), window="1h")
        assert result["violation_count"] == 0

    def test_constant_values_beyond_window_flagged(self):
        # 4 hourly observations all same value; after 1h window, T=1h, T=2h, T=3h are eligible
        result = check_persistence(_hourly([5.0, 5.0, 5.0, 5.0]), window="1h")
        assert result["violation_count"] == 3

    def test_first_window_observations_not_flagged(self):
        # Only 2 observations; second is at T+1h exactly (at window boundary), first is excluded
        result = check_persistence(_hourly([5.0, 5.0]), window="2h")
        assert result["violation_count"] == 0

    def test_value_changes_within_window_not_flagged(self):
        # Values change every observation — rolling min != max throughout
        result = check_persistence(_hourly([1.0, 2.0, 1.0, 2.0, 1.0]), window="2h")
        assert result["violation_count"] == 0

    def test_violation_timestamps_correspond_to_stuck_points(self):
        ts = [_utc(2024, 1, 1, i) for i in range(5)]
        df = _make_df(ts, [1.0, 1.0, 1.0, 1.0, 1.0])
        result = check_persistence(df, window="1h")
        assert len(result["timestamps"]) == result["violation_count"]


class TestCheckPersistenceValueBounds:

    def test_stuck_value_within_range_flagged(self):
        # Sensor stuck at 5.0 (within [0, 10])
        result = check_persistence(_hourly([5.0, 5.0, 5.0, 5.0]), window="1h", min_value=0.0, max_value=10.0)
        assert result["violation_count"] == 3

    def test_stuck_value_outside_range_not_flagged(self):
        # Sensor stuck at 50.0, but bounds are [0, 10] — legitimately out of range, not suspicious stuck
        result = check_persistence(_hourly([50.0, 50.0, 50.0, 50.0]), window="1h", min_value=0.0, max_value=10.0)
        assert result["violation_count"] == 0

    def test_stuck_value_at_min_bound_flagged(self):
        result = check_persistence(_hourly([0.0, 0.0, 0.0, 0.0]), window="1h", min_value=0.0, max_value=10.0)
        assert result["violation_count"] == 3

    def test_stuck_value_at_max_bound_flagged(self):
        result = check_persistence(_hourly([10.0, 10.0, 10.0, 10.0]), window="1h", min_value=0.0, max_value=10.0)
        assert result["violation_count"] == 3

    def test_min_bound_only_filters_stuck_below_min(self):
        # Stuck at -1.0, min_value=0.0 → not in suspicious range
        result = check_persistence(_hourly([-1.0, -1.0, -1.0, -1.0]), window="1h", min_value=0.0)
        assert result["violation_count"] == 0

    def test_max_bound_only_filters_stuck_above_max(self):
        # Stuck at 20.0, max_value=10.0 → not in suspicious range
        result = check_persistence(_hourly([20.0, 20.0, 20.0, 20.0]), window="1h", max_value=10.0)
        assert result["violation_count"] == 0


class TestCheckPersistenceNoDataValue:

    def test_no_data_value_excluded_before_persistence_check(self):
        # All sentinel values → empty DataFrame after filtering → zero violations
        result = check_persistence(_hourly([-9999.0, -9999.0, -9999.0, -9999.0]), window="1h", no_data_value=-9999.0)
        assert result["violation_count"] == 0

    def test_without_no_data_value_sentinel_treated_as_constant_value(self):
        # Without filtering, all -9999.0 values are constant → persistence violations
        result = check_persistence(_hourly([-9999.0, -9999.0, -9999.0, -9999.0]), window="1h")
        assert result["violation_count"] == 3