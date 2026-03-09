import pytest
import pandas as pd
from typing import Literal
from datetime import timezone, timedelta
from zoneinfo import ZoneInfo

from hydroserverpy.etl.models.timestamp import Timestamp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def utc_iso_timestamp():
    return Timestamp(timestamp_type="iso", timezone_type="utc")


@pytest.fixture
def iana_timestamp():
    return Timestamp(timestamp_type="iso", timezone_type="iana", timezone="America/New_York")


@pytest.fixture
def offset_timestamp():
    return Timestamp(timestamp_type="iso", timezone_type="offset", timezone="-0700")


@pytest.fixture
def custom_timestamp():
    return Timestamp(timestamp_type="custom", timestamp_format="%Y-%m-%d %H:%M:%S", timezone_type="utc")


# ---------------------------------------------------------------------------
# Model validation – timestamp_type / timestamp_format
# ---------------------------------------------------------------------------

class TestTimestampFormatValidation:

    def test_custom_type_requires_format(self):
        with pytest.raises(ValueError, match="Timestamp format is required"):
            Timestamp(timestamp_type="custom", timezone_type="utc")

    def test_non_custom_type_rejects_format(self):
        with pytest.raises(ValueError, match="Timestamp formats may only be used"):
            Timestamp(timestamp_type="iso", timestamp_format="%Y-%m-%d", timezone_type="utc")

    @pytest.mark.parametrize("fmt", [
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%Y%m%dT%H%M%S",
        "%m-%d-%Y %I:%M %p",
    ])
    def test_valid_custom_formats(self, fmt):
        ts = Timestamp(timestamp_type="custom", timestamp_format=fmt, timezone_type="utc")
        assert ts.timestamp_format == fmt

    def test_iso_type_without_format(self):
        ts = Timestamp(timestamp_type="iso", timezone_type="utc")
        assert ts.timestamp_format is None


# ---------------------------------------------------------------------------
# Model validation – timezone
# ---------------------------------------------------------------------------

class TestTimezoneValidation:

    @pytest.mark.parametrize("tz_type", ["offset", "iana"])
    def test_offset_and_iana_require_timezone(self, tz_type: Literal["offset", "iana"]):
        with pytest.raises(ValueError, match="Timezone offset must be provided"):
            Timestamp(timestamp_type="iso", timezone_type=tz_type)

    @pytest.mark.parametrize("bad_offset", [
        "0700",       # missing sign
        "+700",       # only 3 digits, no colon
        "+07000",     # too many digits
        "+1500",      # hours > 14
        "+1401",      # hours==14 but minutes != 0
        "+0760",      # minutes >= 60
        "UTC+07",     # wrong format entirely
        "+15:00",     # colon form, hours > 14
        "+14:01",     # colon form, hours==14 but minutes != 0
        "+07:60",     # colon form, minutes >= 60
        "+05:3",      # colon form but wrong digit count
    ])
    def test_invalid_utc_offsets(self, bad_offset):
        with pytest.raises(ValueError, match="Invalid timestamp UTC offset"):
            Timestamp(timestamp_type="iso", timezone_type="offset", timezone=bad_offset)

    @pytest.mark.parametrize("good_offset", [
        "+0000", "-0000", "+1400", "-1200", "+0530", "-0730",
        "+00:00", "-00:00", "+14:00", "-12:00", "+05:30", "-07:30",
    ])
    def test_valid_utc_offsets(self, good_offset):
        ts = Timestamp(timestamp_type="iso", timezone_type="offset", timezone=good_offset)
        assert ts.timezone == good_offset

    def test_invalid_iana_timezone(self):
        with pytest.raises(ValueError, match="Invalid IANA timezone"):
            Timestamp(timestamp_type="iso", timezone_type="iana", timezone="Not/ATimezone")

    @pytest.mark.parametrize("iana_tz", [
        "America/New_York", "Europe/London", "Asia/Tokyo", "UTC", "US/Pacific",
    ])
    def test_valid_iana_timezones(self, iana_tz):
        ts = Timestamp(timestamp_type="iso", timezone_type="iana", timezone=iana_tz)
        assert ts.timezone == iana_tz

    def test_none_timezone_type_rejects_explicit_timezone(self):
        with pytest.raises(ValueError, match="Default timezone value must not be provided"):
            Timestamp(timestamp_type="iso", timezone_type=None, timezone="UTC")

    def test_none_timezone_type_without_value_is_valid(self):
        ts = Timestamp(timestamp_type="iso", timezone_type=None)
        assert ts.timezone_type is None
        assert ts.timezone is None

    def test_timezone_type_defaults_to_none(self):
        ts = Timestamp(timestamp_type="iso")
        assert ts.timezone_type is None


# ---------------------------------------------------------------------------
# _to_pandas_offset
# ---------------------------------------------------------------------------

class TestToPandasOffset:

    @pytest.mark.parametrize("value,expected", [
        ("+0530",  "+05:30"),
        ("-0700",  "-07:00"),
        ("+0000",  "+00:00"),
        ("-1200",  "-12:00"),
        ("+1400",  "+14:00"),
        ("+05:30", "+05:30"),   # already has colon – unchanged
        ("-07:00", "-07:00"),   # already has colon – unchanged
    ])
    def test_normalises_to_colon_form(self, value, expected):
        assert Timestamp._to_pandas_offset(value) == expected

    def test_idempotent_on_colon_form(self):
        assert Timestamp._to_pandas_offset("+05:30") == "+05:30"

    def test_preserves_sign(self):
        assert Timestamp._to_pandas_offset("-0530").startswith("-")
        assert Timestamp._to_pandas_offset("+0530").startswith("+")


# ---------------------------------------------------------------------------
# .tz cached property
# ---------------------------------------------------------------------------

class TestTzProperty:

    def test_utc_type_returns_utc(self, utc_iso_timestamp):
        assert utc_iso_timestamp.tz == timezone.utc

    def test_iana_type_returns_zone_info(self, iana_timestamp):
        assert iana_timestamp.tz == ZoneInfo("America/New_York")

    def test_none_timezone_type_returns_none(self):
        ts = Timestamp(timestamp_type="iso", timezone_type=None)
        assert ts.tz is None

    @pytest.mark.parametrize("offset,expected_minutes", [
        ("+0700",  7 * 60),
        ("-0530",  -(5 * 60 + 30)),
        ("+0000",  0),
        ("-1200",  -12 * 60),
        ("+07:00", 7 * 60),       # colon form
        ("-05:30", -(5 * 60 + 30)),  # colon form
    ])
    def test_offset_type_returns_correct_offset(self, offset, expected_minutes):
        ts = Timestamp(timestamp_type="iso", timezone_type="offset", timezone=offset)
        assert ts.tz == timezone(timedelta(minutes=expected_minutes))


# ---------------------------------------------------------------------------
# parse_series_to_utc – UTC timezone type
# ---------------------------------------------------------------------------

class TestParseSeriesUtc:

    def test_basic_utc_iso_strings(self, utc_iso_timestamp):
        series = pd.Series(["2024-01-01T00:00:00", "2024-06-15T12:30:00"])
        result = utc_iso_timestamp.parse_series_to_utc(series)
        assert result.dt.tz == timezone.utc
        assert result.iloc[0] == pd.Timestamp("2024-01-01 00:00:00", tz="UTC")
        assert result.iloc[1] == pd.Timestamp("2024-06-15 12:30:00", tz="UTC")

    def test_invalid_strings_become_nat(self, utc_iso_timestamp):
        series = pd.Series(["not-a-date", "also-bad"])
        result = utc_iso_timestamp.parse_series_to_utc(series)
        assert result.isna().all()

    def test_mixed_valid_invalid(self, utc_iso_timestamp):
        series = pd.Series(["2024-01-01T00:00:00", "bad-date", "2024-06-01T00:00:00"])
        result = utc_iso_timestamp.parse_series_to_utc(series)
        assert pd.notna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert pd.notna(result.iloc[2])

    def test_whitespace_is_stripped(self, utc_iso_timestamp):
        series = pd.Series(["  2024-01-01T12:00:00  ", "\t2024-06-01T00:00:00\n"])
        result = utc_iso_timestamp.parse_series_to_utc(series)
        assert pd.notna(result.iloc[0])
        assert pd.notna(result.iloc[1])

    def test_empty_series_returns_empty(self, utc_iso_timestamp):
        series = pd.Series([], dtype="object")
        result = utc_iso_timestamp.parse_series_to_utc(series)
        assert len(result) == 0

    def test_already_datetime64_dtype_input(self, utc_iso_timestamp):
        series = pd.to_datetime(pd.Series(["2024-01-01", "2024-06-15"]))
        assert pd.api.types.is_datetime64_any_dtype(series)
        result = utc_iso_timestamp.parse_series_to_utc(series)
        assert result.dt.tz == timezone.utc


# ---------------------------------------------------------------------------
# parse_series_to_utc – None timezone type (embedded offsets in source data)
# ---------------------------------------------------------------------------

class TestParseSeriesNoneTimezone:

    def test_embedded_offsets_are_converted_to_utc(self):
        ts = Timestamp(timestamp_type="iso", timezone_type=None)
        series = pd.Series(["2024-01-01T00:00:00+05:30", "2024-01-01T00:00:00-07:00"])
        result = ts.parse_series_to_utc(series)
        assert result.dt.tz == timezone.utc
        assert result.iloc[0] == pd.Timestamp("2023-12-31 18:30:00", tz="UTC")
        assert result.iloc[1] == pd.Timestamp("2024-01-01 07:00:00", tz="UTC")

    def test_naive_strings_fall_back_to_utc(self):
        ts = Timestamp(timestamp_type="iso", timezone_type=None)
        series = pd.Series(["2024-01-01T00:00:00"])
        result = ts.parse_series_to_utc(series)
        assert result.dt.tz == timezone.utc
        assert result.iloc[0] == pd.Timestamp("2024-01-01 00:00:00", tz="UTC")

    def test_mixed_offset_series_is_flattened_to_utc(self):
        ts = Timestamp(timestamp_type="iso", timezone_type=None)
        series = pd.Series(["2024-01-01T00:00:00+02:00", "2024-01-01T00:00:00-05:00"])
        result = ts.parse_series_to_utc(series)
        assert result.dt.tz == timezone.utc
        assert result.iloc[0] == pd.Timestamp("2023-12-31 22:00:00", tz="UTC")
        assert result.iloc[1] == pd.Timestamp("2024-01-01 05:00:00", tz="UTC")


# ---------------------------------------------------------------------------
# parse_series_to_utc – IANA timezone type
# ---------------------------------------------------------------------------

class TestParseSeriesIana:

    def test_naive_strings_localized_to_iana_zone(self, iana_timestamp):
        # America/New_York is UTC-5 in January
        series = pd.Series(["2024-01-01T00:00:00"])
        result = iana_timestamp.parse_series_to_utc(series)
        assert result.dt.tz == timezone.utc
        assert result.iloc[0] == pd.Timestamp("2024-01-01 05:00:00", tz="UTC")

    def test_embedded_offsets_are_overwritten_by_iana_zone(self, iana_timestamp):
        # Embedded +05:30 is stripped; America/New_York (UTC-5 in Jan) applied instead
        series = pd.Series(["2024-01-01T00:00:00+05:30"])
        result = iana_timestamp.parse_series_to_utc(series)
        assert result.iloc[0] == pd.Timestamp("2024-01-01 05:00:00", tz="UTC")

    def test_dst_spring_forward(self):
        ts = Timestamp(timestamp_type="iso", timezone_type="iana", timezone="America/New_York")
        # Post spring-forward: America/New_York is UTC-4 (EDT)
        series = pd.Series(["2024-03-10T03:00:00"])
        result = ts.parse_series_to_utc(series)
        assert result.dt.tz == timezone.utc
        assert result.iloc[0] == pd.Timestamp("2024-03-10 07:00:00", tz="UTC")


# ---------------------------------------------------------------------------
# parse_series_to_utc – offset timezone type
# ---------------------------------------------------------------------------

class TestParseSeriesOffset:

    def test_naive_strings_localized_to_offset(self, offset_timestamp):
        # -0700 => add 7h to get UTC
        series = pd.Series(["2024-01-01T00:00:00"])
        result = offset_timestamp.parse_series_to_utc(series)
        assert result.dt.tz == timezone.utc
        assert result.iloc[0] == pd.Timestamp("2024-01-01 07:00:00", tz="UTC")

    def test_embedded_offsets_are_overwritten_by_configured_offset(self, offset_timestamp):
        # Embedded +05:30 is stripped; -0700 applied instead
        series = pd.Series(["2024-01-01T00:00:00+05:30"])
        result = offset_timestamp.parse_series_to_utc(series)
        assert result.iloc[0] == pd.Timestamp("2024-01-01 07:00:00", tz="UTC")

    def test_positive_offset_bare_format(self):
        ts = Timestamp(timestamp_type="iso", timezone_type="offset", timezone="+0530")
        series = pd.Series(["2024-01-01T00:00:00"])
        result = ts.parse_series_to_utc(series)
        assert result.iloc[0] == pd.Timestamp("2023-12-31 18:30:00", tz="UTC")

    def test_positive_offset_colon_format(self):
        ts = Timestamp(timestamp_type="iso", timezone_type="offset", timezone="+05:30")
        series = pd.Series(["2024-01-01T00:00:00"])
        result = ts.parse_series_to_utc(series)
        assert result.iloc[0] == pd.Timestamp("2023-12-31 18:30:00", tz="UTC")

    def test_bare_and_colon_formats_produce_identical_results(self):
        bare = Timestamp(timestamp_type="iso", timezone_type="offset", timezone="+0530")
        colon = Timestamp(timestamp_type="iso", timezone_type="offset", timezone="+05:30")
        series = pd.Series(["2024-06-15T12:00:00"])
        assert bare.parse_series_to_utc(series).iloc[0] == colon.parse_series_to_utc(series).iloc[0]

    def test_negative_offset_bare_format(self):
        ts = Timestamp(timestamp_type="iso", timezone_type="offset", timezone="-0700")
        series = pd.Series(["2024-01-01T00:00:00"])
        result = ts.parse_series_to_utc(series)
        assert result.iloc[0] == pd.Timestamp("2024-01-01 07:00:00", tz="UTC")

    def test_negative_offset_colon_format(self):
        ts = Timestamp(timestamp_type="iso", timezone_type="offset", timezone="-07:00")
        series = pd.Series(["2024-01-01T00:00:00"])
        result = ts.parse_series_to_utc(series)
        assert result.iloc[0] == pd.Timestamp("2024-01-01 07:00:00", tz="UTC")


# ---------------------------------------------------------------------------
# parse_series_to_utc – custom format
# ---------------------------------------------------------------------------

class TestParseSeriesCustomFormat:

    def test_custom_format_parses_correctly(self, custom_timestamp):
        series = pd.Series(["2024-03-15 08:00:00", "2024-12-31 23:59:59"])
        result = custom_timestamp.parse_series_to_utc(series)
        assert result.dt.tz == timezone.utc
        assert result.iloc[0] == pd.Timestamp("2024-03-15 08:00:00", tz="UTC")

    def test_custom_format_wrong_data_becomes_nat(self, custom_timestamp):
        series = pd.Series(["2024-01-01T00:00:00Z"])
        result = custom_timestamp.parse_series_to_utc(series)
        assert result.isna().all()

    def test_custom_format_with_iana_timezone(self):
        ts = Timestamp(
            timestamp_type="custom",
            timestamp_format="%Y-%m-%d %H:%M:%S",
            timezone_type="iana",
            timezone="America/Chicago",
        )
        # America/Chicago is UTC-6 in January
        series = pd.Series(["2024-01-01 00:00:00"])
        result = ts.parse_series_to_utc(series)
        assert result.iloc[0] == pd.Timestamp("2024-01-01 06:00:00", tz="UTC")

    def test_custom_format_with_offset_bare(self):
        ts = Timestamp(
            timestamp_type="custom",
            timestamp_format="%Y-%m-%d %H:%M:%S",
            timezone_type="offset",
            timezone="+0200",
        )
        series = pd.Series(["2024-01-01 00:00:00"])
        result = ts.parse_series_to_utc(series)
        assert result.iloc[0] == pd.Timestamp("2023-12-31 22:00:00", tz="UTC")

    def test_custom_format_with_offset_colon(self):
        ts = Timestamp(
            timestamp_type="custom",
            timestamp_format="%Y-%m-%d %H:%M:%S",
            timezone_type="offset",
            timezone="+02:00",
        )
        series = pd.Series(["2024-01-01 00:00:00"])
        result = ts.parse_series_to_utc(series)
        assert result.iloc[0] == pd.Timestamp("2023-12-31 22:00:00", tz="UTC")


# ---------------------------------------------------------------------------
# parse_series_to_utc – result dtype consistency
# ---------------------------------------------------------------------------

class TestParseSeriesResultDtype:

    @pytest.mark.parametrize("tz_type,kwargs", [
        ("utc",  {}),
        (None,     {}),
        ("iana",  {"timezone": "America/New_York"}),
        ("offset", {"timezone": "-0500"}),
        ("offset", {"timezone": "-05:00"}),
    ])
    def test_result_is_always_utc_aware(self, tz_type, kwargs):
        ts = Timestamp(timestamp_type="iso", timezone_type=tz_type, **kwargs)
        series = pd.Series(["2024-01-01T00:00:00"])
        result = ts.parse_series_to_utc(series)
        assert result.dt.tz == timezone.utc

    def test_large_series_completes(self, utc_iso_timestamp):
        dates = pd.date_range("2000-01-01", periods=100_000, freq="s").astype(str)
        result = utc_iso_timestamp.parse_series_to_utc(pd.Series(dates))
        assert len(result) == 100_000
        assert result.isna().sum() == 0
