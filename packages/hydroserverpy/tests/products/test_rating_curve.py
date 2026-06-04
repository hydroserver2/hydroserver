import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone

from hydroserverpy.products.rating_curve import apply_rating_curve
from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _utc(year, month, day, hour=0):
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def _make_df(timestamps, values):
    return pd.DataFrame({
        TIMESTAMP_COL: pd.DatetimeIndex(timestamps).as_unit("us"),
        RESULT_COL: np.array(list(values), dtype=np.float64),
    })


def _daily(count):
    return [_utc(2024, 1, d) for d in range(1, count + 1)]


LINEAR_BREAKPOINTS = [(0.0, 0.0), (10.0, 100.0)]
MULTI_SEGMENT_BREAKPOINTS = [(0.0, 0.0), (5.0, 50.0), (10.0, 200.0)]
POWER_LAW_BREAKPOINTS = [(1.0, 1.0), (4.0, 2.0), (9.0, 3.0)]  # fits y = sqrt(x)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestApplyRatingCurveValidation:

    def test_fewer_than_two_breakpoints_raises(self):
        df = _make_df(_daily(3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="2 breakpoints"):
            apply_rating_curve(df, breakpoints=[(0.0, 0.0)])

    def test_empty_breakpoints_raises(self):
        df = _make_df(_daily(3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError):
            apply_rating_curve(df, breakpoints=[])

    def test_power_law_with_non_positive_breakpoint_x_raises(self):
        df = _make_df(_daily(1), [1.0])
        with pytest.raises(ValueError, match="positive"):
            apply_rating_curve(df, breakpoints=[(0.0, 0.0), (1.0, 1.0)], method="power_law")

    def test_power_law_with_non_positive_breakpoint_y_raises(self):
        df = _make_df(_daily(1), [1.0])
        with pytest.raises(ValueError, match="positive"):
            apply_rating_curve(df, breakpoints=[(1.0, 0.0), (2.0, 1.0)], method="power_law")


# ---------------------------------------------------------------------------
# Linear interpolation
# ---------------------------------------------------------------------------

class TestApplyRatingCurveLinear:

    def test_midpoint_is_interpolated(self):
        df = _make_df(_daily(1), [5.0])
        result = apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS)
        assert result[RESULT_COL].iloc[0] == pytest.approx(50.0)

    def test_exact_lower_breakpoint(self):
        df = _make_df(_daily(1), [0.0])
        result = apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS)
        assert result[RESULT_COL].iloc[0] == pytest.approx(0.0)

    def test_exact_upper_breakpoint(self):
        df = _make_df(_daily(1), [10.0])
        result = apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS)
        assert result[RESULT_COL].iloc[0] == pytest.approx(100.0)

    def test_multi_segment_lower_segment(self):
        df = _make_df(_daily(1), [2.5])
        result = apply_rating_curve(df, breakpoints=MULTI_SEGMENT_BREAKPOINTS)
        assert result[RESULT_COL].iloc[0] == pytest.approx(25.0)

    def test_multi_segment_upper_segment(self):
        # Between 5 and 10: slope is (200-50)/(10-5) = 30 per unit
        df = _make_df(_daily(1), [7.5])
        result = apply_rating_curve(df, breakpoints=MULTI_SEGMENT_BREAKPOINTS)
        assert result[RESULT_COL].iloc[0] == pytest.approx(125.0)

    def test_breakpoints_are_sorted_before_use(self):
        reversed_bps = list(reversed(LINEAR_BREAKPOINTS))
        df = _make_df(_daily(1), [5.0])
        result = apply_rating_curve(df, breakpoints=reversed_bps)
        assert result[RESULT_COL].iloc[0] == pytest.approx(50.0)

    def test_multiple_rows_are_all_transformed(self):
        df = _make_df(_daily(3), [2.5, 5.0, 7.5])
        result = apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS)
        assert len(result) == 3
        assert result[RESULT_COL].tolist() == pytest.approx([25.0, 50.0, 75.0])

    def test_output_result_dtype_is_float64(self):
        df = _make_df(_daily(1), [5.0])
        result = apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS)
        assert pd.api.types.is_float_dtype(result[RESULT_COL])

    def test_output_schema_matches_canonical(self):
        df = _make_df(_daily(1), [5.0])
        result = apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS)
        assert pd.api.types.is_datetime64_any_dtype(result[TIMESTAMP_COL])
        assert pd.api.types.is_float_dtype(result[RESULT_COL])

    def test_timestamps_are_preserved(self):
        ts = _daily(3)
        df = _make_df(ts, [2.5, 5.0, 7.5])
        result = apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS)
        assert result[TIMESTAMP_COL].tolist() == df[TIMESTAMP_COL].tolist()


# ---------------------------------------------------------------------------
# Power law interpolation
# ---------------------------------------------------------------------------

class TestApplyRatingCurvePowerLaw:

    def test_exact_breakpoint_matches(self):
        df = _make_df(_daily(1), [4.0])
        result = apply_rating_curve(df, breakpoints=POWER_LAW_BREAKPOINTS, method="power_law")
        assert result[RESULT_COL].iloc[0] == pytest.approx(2.0, rel=1e-3)

    def test_sqrt_fit_at_known_point(self):
        # POWER_LAW_BREAKPOINTS fits y = sqrt(x); at x=9, y=3
        df = _make_df(_daily(1), [9.0])
        result = apply_rating_curve(df, breakpoints=POWER_LAW_BREAKPOINTS, method="power_law")
        assert result[RESULT_COL].iloc[0] == pytest.approx(3.0, rel=1e-3)

    def test_non_positive_stage_is_out_of_range_with_drop(self):
        df = _make_df(_daily(2), [0.0, 4.0])
        result = apply_rating_curve(df, breakpoints=POWER_LAW_BREAKPOINTS, method="power_law", out_of_range="drop")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# out_of_range behavior
# ---------------------------------------------------------------------------

class TestApplyRatingCurveOutOfRange:

    def test_out_of_range_drop_removes_row(self):
        df = _make_df(_daily(3), [-1.0, 5.0, 15.0])
        result = apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS, out_of_range="drop")
        assert len(result) == 1
        assert result[RESULT_COL].iloc[0] == pytest.approx(50.0)

    def test_out_of_range_drop_all_in_range_returns_all_rows(self):
        df = _make_df(_daily(3), [2.0, 5.0, 8.0])
        result = apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS, out_of_range="drop")
        assert len(result) == 3

    def test_out_of_range_raise_raises_for_below_range(self):
        df = _make_df(_daily(1), [-1.0])
        with pytest.raises(ValueError, match="outside the valid range"):
            apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS, out_of_range="raise")

    def test_out_of_range_raise_raises_for_above_range(self):
        df = _make_df(_daily(1), [99.0])
        with pytest.raises(ValueError, match="outside the valid range"):
            apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS, out_of_range="raise")

    def test_out_of_range_raise_passes_when_all_in_range(self):
        df = _make_df(_daily(2), [5.0, 8.0])
        result = apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS, out_of_range="raise")
        assert len(result) == 2

    def test_out_of_range_stop_truncates_before_first_out_of_range(self):
        df = _make_df(_daily(4), [2.0, 5.0, 15.0, 8.0])
        result = apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS, out_of_range="stop")
        assert len(result) == 2

    def test_out_of_range_stop_returns_all_rows_when_all_in_range(self):
        df = _make_df(_daily(3), [2.0, 5.0, 8.0])
        result = apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS, out_of_range="stop")
        assert len(result) == 3

    def test_out_of_range_stop_returns_empty_when_first_row_out_of_range(self):
        df = _make_df(_daily(3), [99.0, 5.0, 8.0])
        result = apply_rating_curve(df, breakpoints=LINEAR_BREAKPOINTS, out_of_range="stop")
        assert len(result) == 0