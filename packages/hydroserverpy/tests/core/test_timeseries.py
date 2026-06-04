import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone

from hydroserverpy.core.timeseries import (
    TIMESTAMP_COL, RESULT_COL,
    validate_timeseries, align_timeseries, normalize_tz,
)


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


def _hourly(start, count):
    return [_utc(2024, 1, 1, start + i) for i in range(count)]


# ---------------------------------------------------------------------------
# validate_timeseries
# ---------------------------------------------------------------------------

class TestValidateTimeseries:

    def test_valid_df_passes(self):
        df = _make_df([_utc(2024, 1, 1)], [1.0])
        validate_timeseries(df)

    def test_missing_timestamp_column_raises(self):
        df = pd.DataFrame({RESULT_COL: pd.array([1.0], dtype="float64")})
        with pytest.raises(ValueError, match=TIMESTAMP_COL):
            validate_timeseries(df)

    def test_missing_result_column_raises(self):
        df = pd.DataFrame({TIMESTAMP_COL: pd.DatetimeIndex([_utc(2024, 1, 1)]).as_unit("us")})
        with pytest.raises(ValueError, match=RESULT_COL):
            validate_timeseries(df)

    def test_non_coercible_timestamp_raises(self):
        df = pd.DataFrame({
            TIMESTAMP_COL: pd.array(["not a date"], dtype=object),
            RESULT_COL: pd.array([1.0], dtype="float64"),
        })
        with pytest.raises(ValueError):
            validate_timeseries(df)

    def test_non_numeric_result_raises(self):
        df = pd.DataFrame({
            TIMESTAMP_COL: pd.DatetimeIndex([_utc(2024, 1, 1)]).as_unit("us"),
            RESULT_COL: pd.array(["not a number"], dtype=object),
        })
        with pytest.raises(ValueError):
            validate_timeseries(df)

    def test_nat_in_timestamp_raises(self):
        df = pd.DataFrame({
            TIMESTAMP_COL: pd.array([None], dtype="datetime64[us, UTC]"),
            RESULT_COL: pd.array([1.0], dtype="float64"),
        })
        with pytest.raises(ValueError):
            validate_timeseries(df)

    def test_nan_in_result_raises(self):
        df = _make_df([_utc(2024, 1, 1)], [float("nan")])
        with pytest.raises(ValueError):
            validate_timeseries(df)

    def test_extra_columns_are_allowed(self):
        df = _make_df([_utc(2024, 1, 1)], [1.0]).assign(extra=42)
        validate_timeseries(df)

    def test_coerces_and_returns_dataframe(self):
        df = _make_df([_utc(2024, 1, 1)], [1.0])
        result = validate_timeseries(df)
        assert pd.api.types.is_datetime64_any_dtype(result[TIMESTAMP_COL])
        assert pd.api.types.is_float_dtype(result[RESULT_COL])

    def test_output_schema_matches_canonical(self):
        df = _make_df([_utc(2024, 1, 1)], [1.0])
        result = validate_timeseries(df)
        assert pd.api.types.is_datetime64_any_dtype(result[TIMESTAMP_COL])
        assert pd.api.types.is_float_dtype(result[RESULT_COL])


# ---------------------------------------------------------------------------
# align_timeseries
# ---------------------------------------------------------------------------

class TestAlignTimeseries:

    def test_all_on_grid_returns_all_rows(self):
        df = _make_df(_hourly(0, 5), [float(i) for i in range(5)])
        result = align_timeseries(df, interval="1h")
        assert len(result) == 5

    def test_output_schema_matches_canonical(self):
        df = _make_df(_hourly(0, 3), [1.0, 2.0, 3.0])
        result = align_timeseries(df, interval="1h")
        assert pd.api.types.is_datetime64_any_dtype(result[TIMESTAMP_COL])
        assert pd.api.types.is_float_dtype(result[RESULT_COL])

    def test_on_missing_drop_removes_gap_rows(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [1.0, 3.0])
        result = align_timeseries(df, interval="1h", on_missing="drop")
        assert len(result) == 2
        assert result[RESULT_COL].isna().sum() == 0

    def test_on_missing_raise_raises_when_gap_present(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [1.0, 3.0])
        with pytest.raises(ValueError):
            align_timeseries(df, interval="1h", on_missing="raise")

    def test_on_missing_raise_passes_when_no_gap(self):
        df = _make_df(_hourly(0, 4), [float(i) for i in range(4)])
        result = align_timeseries(df, interval="1h", on_missing="raise")
        assert len(result) == 4

    def test_on_missing_stop_truncates_at_first_gap(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 1), _utc(2024, 1, 1, 3)]
        df = _make_df(ts, [1.0, 2.0, 4.0])
        result = align_timeseries(df, interval="1h", on_missing="stop")
        assert len(result) == 2

    def test_on_missing_stop_returns_full_series_when_no_gap(self):
        df = _make_df(_hourly(0, 4), [float(i) for i in range(4)])
        result = align_timeseries(df, interval="1h", on_missing="stop")
        assert len(result) == 4

    def test_on_missing_interpolate_fills_midpoint_linearly(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [0.0, 2.0])
        result = align_timeseries(df, interval="1h", on_missing="interpolate")
        assert len(result) == 3
        assert result[RESULT_COL].isna().sum() == 0
        mid_val = result.sort_values(TIMESTAMP_COL)[RESULT_COL].iloc[1]
        assert mid_val == pytest.approx(1.0)

    def test_on_missing_interpolate_nearest_fills_gap(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [1.0, 3.0])
        result = align_timeseries(df, interval="1h", on_missing="interpolate", interpolation="nearest")
        assert len(result) == 3
        assert result[RESULT_COL].isna().sum() == 0

    def test_max_gap_leaves_wide_gaps_as_null(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 1), _utc(2024, 1, 1, 4), _utc(2024, 1, 1, 5)]
        df = _make_df(ts, [0.0, 1.0, 4.0, 5.0])
        result = align_timeseries(df, interval="1h", on_missing="interpolate", max_gap="2h")
        assert len(result) == 6
        assert result[RESULT_COL].isna().sum() == 2

    def test_max_gap_within_threshold_is_interpolated(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [0.0, 2.0])
        result = align_timeseries(df, interval="1h", on_missing="interpolate", max_gap="3h")
        assert result[RESULT_COL].isna().sum() == 0

    def test_max_gap_without_interpolate_raises(self):
        df = _make_df(_hourly(0, 3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError):
            align_timeseries(df, interval="1h", on_missing="drop", max_gap="2h")

    def test_interpolation_without_interpolate_raises(self):
        df = _make_df(_hourly(0, 3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError):
            align_timeseries(df, interval="1h", on_missing="drop", interpolation="nearest")

    def test_anchor_shifts_grid_to_match_offset_timestamps(self):
        anchor = _utc(2024, 1, 1, 0, 30)
        ts = [_utc(2024, 1, 1, 0, 30), _utc(2024, 1, 1, 1, 30), _utc(2024, 1, 1, 2, 30)]
        df = _make_df(ts, [1.0, 2.0, 3.0])
        result = align_timeseries(df, interval="1h", anchor=anchor, on_missing="raise")
        assert len(result) == 3

    def test_single_row_input_returns_single_row(self):
        df = _make_df([_utc(2024, 1, 1, 0)], [1.0])
        result = align_timeseries(df, interval="1h")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# normalize_tz
# ---------------------------------------------------------------------------

class TestNormalizeTz:

    def test_iana_name_passes_through(self):
        assert normalize_tz("America/Denver") == "America/Denver"

    def test_utc_passes_through(self):
        assert normalize_tz("UTC") == "UTC"

    def test_etc_gmt_name_passes_through(self):
        assert normalize_tz("Etc/GMT+5") == "Etc/GMT+5"

    def test_positive_offset_with_colon_converts_to_etc_gmt(self):
        assert normalize_tz("+05:00") == "Etc/GMT-5"

    def test_negative_offset_with_colon_converts_to_etc_gmt(self):
        assert normalize_tz("-07:00") == "Etc/GMT+7"

    def test_positive_offset_without_colon_converts_to_etc_gmt(self):
        assert normalize_tz("+0500") == "Etc/GMT-5"

    def test_negative_offset_without_colon_converts_to_etc_gmt(self):
        assert normalize_tz("-0700") == "Etc/GMT+7"

    def test_zero_offset_returns_utc(self):
        assert normalize_tz("+00:00") == "UTC"

    def test_zero_offset_negative_returns_utc(self):
        assert normalize_tz("-00:00") == "UTC"

    def test_non_whole_hour_offset_raises(self):
        with pytest.raises(ValueError, match="non-zero minute"):
            normalize_tz("+05:30")

    def test_offset_beyond_14_hours_raises(self):
        with pytest.raises(ValueError):
            normalize_tz("+15:00")

    def test_invalid_iana_name_raises(self):
        with pytest.raises(ValueError):
            normalize_tz("Not/ATimezone")

    def test_etc_gmt_sign_convention_is_reversed(self):
        result = normalize_tz("+05:00")
        assert result == "Etc/GMT-5"
