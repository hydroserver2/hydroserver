import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone

from hydroserverpy.core.timeseries import (
    TIMESTAMP_COL, RESULT_COL,
    validate_timeseries, normalize_tz,
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
