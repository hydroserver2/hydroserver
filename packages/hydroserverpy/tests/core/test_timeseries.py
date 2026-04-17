import polars as pl
import pytest
from datetime import datetime, timezone

from hydroserverpy.core.timeseries import (
    TIMESTAMP_COL, RESULT_COL, SCHEMA,
    validate_timeseries, align_timeseries, normalize_tz,
)


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
        df = pl.DataFrame({RESULT_COL: pl.Series([1.0], dtype=pl.Float64)})
        with pytest.raises(ValueError, match=TIMESTAMP_COL):
            validate_timeseries(df)

    def test_missing_result_column_raises(self):
        us = [int(_utc(2024, 1, 1).timestamp() * 1_000_000)]
        df = pl.DataFrame({TIMESTAMP_COL: pl.Series(us, dtype=pl.Int64).cast(pl.Datetime("us", "UTC"))})
        with pytest.raises(ValueError, match=RESULT_COL):
            validate_timeseries(df)

    def test_wrong_timestamp_dtype_raises(self):
        df = pl.DataFrame({
            TIMESTAMP_COL: pl.Series([1_000_000], dtype=pl.Int64),
            RESULT_COL: pl.Series([1.0], dtype=pl.Float64),
        })
        with pytest.raises(ValueError):
            validate_timeseries(df)

    def test_wrong_result_dtype_raises(self):
        df = _make_df([_utc(2024, 1, 1)], [1.0]).with_columns(
            pl.col(RESULT_COL).cast(pl.Int32)
        )
        with pytest.raises(ValueError):
            validate_timeseries(df)

    def test_extra_columns_are_allowed(self):
        df = _make_df([_utc(2024, 1, 1)], [1.0]).with_columns(pl.lit(42).alias("extra"))
        validate_timeseries(df)

    def test_output_schema_matches_canonical(self):
        df = _make_df([_utc(2024, 1, 1)], [1.0])
        assert df.schema[TIMESTAMP_COL] == SCHEMA[TIMESTAMP_COL]
        assert df.schema[RESULT_COL] == SCHEMA[RESULT_COL]


# ---------------------------------------------------------------------------
# align_timeseries
# ---------------------------------------------------------------------------

class TestAlignTimeseries:

    def test_all_on_grid_returns_all_rows(self):
        df = _make_df(_hourly(0, 5), [float(i) for i in range(5)])
        result = align_timeseries(df, interval="1h")
        assert result.height == 5

    def test_output_schema_matches_canonical(self):
        df = _make_df(_hourly(0, 3), [1.0, 2.0, 3.0])
        result = align_timeseries(df, interval="1h")
        assert result.schema[TIMESTAMP_COL] == SCHEMA[TIMESTAMP_COL]
        assert result.schema[RESULT_COL] == SCHEMA[RESULT_COL]

    def test_on_missing_drop_removes_gap_rows(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [1.0, 3.0])
        result = align_timeseries(df, interval="1h", on_missing="drop")
        assert result.height == 2
        assert result[RESULT_COL].null_count() == 0

    def test_on_missing_raise_raises_when_gap_present(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [1.0, 3.0])
        with pytest.raises(ValueError):
            align_timeseries(df, interval="1h", on_missing="raise")

    def test_on_missing_raise_passes_when_no_gap(self):
        df = _make_df(_hourly(0, 4), [float(i) for i in range(4)])
        result = align_timeseries(df, interval="1h", on_missing="raise")
        assert result.height == 4

    def test_on_missing_stop_truncates_at_first_gap(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 1), _utc(2024, 1, 1, 3)]
        df = _make_df(ts, [1.0, 2.0, 4.0])
        result = align_timeseries(df, interval="1h", on_missing="stop")
        assert result.height == 2

    def test_on_missing_stop_returns_full_series_when_no_gap(self):
        df = _make_df(_hourly(0, 4), [float(i) for i in range(4)])
        result = align_timeseries(df, interval="1h", on_missing="stop")
        assert result.height == 4

    def test_on_missing_interpolate_fills_midpoint_linearly(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [0.0, 2.0])
        result = align_timeseries(df, interval="1h", on_missing="interpolate")
        assert result.height == 3
        assert result[RESULT_COL].null_count() == 0
        mid_val = result.sort(TIMESTAMP_COL)[RESULT_COL][1]
        assert mid_val == pytest.approx(1.0)

    def test_on_missing_interpolate_nearest_fills_gap(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [1.0, 3.0])
        result = align_timeseries(df, interval="1h", on_missing="interpolate", interpolation="nearest")
        assert result.height == 3
        assert result[RESULT_COL].null_count() == 0

    def test_max_gap_leaves_wide_gaps_as_null(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 1), _utc(2024, 1, 1, 4), _utc(2024, 1, 1, 5)]
        df = _make_df(ts, [0.0, 1.0, 4.0, 5.0])
        result = align_timeseries(df, interval="1h", on_missing="interpolate", max_gap="2h")
        assert result.height == 6
        assert result[RESULT_COL].null_count() == 2

    def test_max_gap_within_threshold_is_interpolated(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [0.0, 2.0])
        result = align_timeseries(df, interval="1h", on_missing="interpolate", max_gap="3h")
        assert result[RESULT_COL].null_count() == 0

    def test_max_gap_without_interpolate_raises(self):
        df = _make_df(_hourly(0, 3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError):
            align_timeseries(df, interval="1h", on_missing="drop", max_gap="2h")

    def test_interpolation_without_interpolate_raises(self):
        df = _make_df(_hourly(0, 3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError):
            align_timeseries(df, interval="1h", on_missing="drop", interpolation="nearest")

    def test_anchor_shifts_grid_to_match_offset_timestamps(self):
        # Grid anchored at :30 → points land on 00:30, 01:30, 02:30
        anchor = _utc(2024, 1, 1, 0, 30)
        ts = [_utc(2024, 1, 1, 0, 30), _utc(2024, 1, 1, 1, 30), _utc(2024, 1, 1, 2, 30)]
        df = _make_df(ts, [1.0, 2.0, 3.0])
        result = align_timeseries(df, interval="1h", anchor=anchor, on_missing="raise")
        assert result.height == 3

    def test_single_row_input_returns_single_row(self):
        df = _make_df([_utc(2024, 1, 1, 0)], [1.0])
        result = align_timeseries(df, interval="1h")
        assert result.height == 1


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
        # UTC+5 → Etc/GMT-5 (POSIX sign reversal)
        result = normalize_tz("+05:00")
        assert result == "Etc/GMT-5"
