from functools import cached_property
import logging
from datetime import datetime, timedelta, timezone
import re
from typing import Literal, Optional, Union, get_args
from zoneinfo import ZoneInfo
import pandas as pd
from pydantic import BaseModel, Field

TimestampFormat = Literal["ISO8601", "naive", "custom"]
ALLOWED_TIMESTAMP_FORMATS = {m.lower() for m in get_args(TimestampFormat)}
TimezoneMode = Literal["utc", "daylightSavings", "fixedOffset", "embeddedOffset"]
ALLOWED_TIMEZONE_MODES = {m.lower() for m in get_args(TimezoneMode)}

logger = logging.getLogger(__name__)


class Timestamp(BaseModel):
    format: TimestampFormat
    timezone_mode: TimezoneMode = Field("embeddedOffset", alias="timezoneMode")
    custom_format: Optional[str] = Field(None, alias="customFormat")
    timezone: Optional[str] = None
    key: Optional[str] = None


class TimestampParser:
    def __init__(self, raw: Union[Timestamp, dict]):
        if isinstance(raw, dict):
            self.timestamp = Timestamp.model_validate(raw)
        else:
            self.timestamp = raw

        if self.timestamp.format.lower() not in ALLOWED_TIMESTAMP_FORMATS:
            raise ValueError(
                f"timestamp format {self.timestamp.format!r} must be one of {ALLOWED_TIMESTAMP_FORMATS}"
            )

        self.tz_mode = self.timestamp.timezone_mode.lower()
        if self.tz_mode not in ALLOWED_TIMEZONE_MODES and "%" not in self.tz_mode:
            raise ValueError(
                f"timezone mode {self.tz_mode} must be one of {', '.join(ALLOWED_TIMEZONE_MODES)} "
            )

    @cached_property
    def tz(self):
        if self.tz_mode == "fixedoffset":
            if not self.timestamp.timezone:
                raise ValueError(
                    "`timezone` must be set when timezoneMode is fixedOffset (e.g. '-0700')"
                )
            offset = self.timestamp.timezone.strip()
            if len(offset) != 5 or offset[0] not in "+-":
                raise ValueError(f"Invalid timezone: {offset}")
            sign = 1 if offset[0] == "+" else -1
            hrs, mins = int(offset[1:3]), int(offset[3:5])
            return timezone(timedelta(minutes=sign * (hrs * 60 + mins)))
        if self.tz_mode == "daylightsavings":
            if not self.timestamp.timezone:
                raise ValueError(
                    "Task configuration is missing required daylight savings offset (when using daylightSavings mode)."
                )
            try:
                return ZoneInfo(self.timestamp.timezone)
            except Exception as e:
                raise ValueError(
                    f"Invalid timezone {self.timestamp.timezone!r}. Use an IANA timezone like 'America/Denver'."
                ) from e
        if self.tz_mode == "utc":
            return timezone.utc

    def _convert_series_to_UTC(self, s: pd.Series):
        timestamp_fmt = self.timestamp.format.lower()

        if timestamp_fmt == "iso8601":
            return pd.to_datetime(s, utc=True, errors="coerce")

        if timestamp_fmt == "custom":
            pattern = self.timestamp.custom_format or ""
            naive = pd.to_datetime(s, format=pattern, errors="coerce")
        else:
            naive = pd.to_datetime(s, errors="coerce")

        tz_mode = self.timestamp.timezone_mode.lower()
        if tz_mode == "utc":
            return pd.to_datetime(naive, utc=True, errors="coerce")

        localized = naive.dt.tz_localize(self.tz)
        return localized.dt.tz_convert(timezone.utc)

    def parse_series(self, raw_series: pd.Series) -> pd.Series:
        if pd.api.types.is_datetime64_any_dtype(raw_series):
            s = raw_series  # already datetimes
        else:
            s = raw_series.astype("string", copy=False).str.strip()
        parsed = self._convert_series_to_UTC(s)

        if parsed.isna().any():
            bad_rows = s[parsed.isna()].head(2).tolist()
            logger.warning(
                "%s timestamps failed to parse (format=%r, timezoneMode=%r, timezone=%r, customFormat=%r). Sample bad values: %s",
                parsed.isna().sum(),
                self.timestamp.format,
                self.timestamp.timezone_mode,
                self.timestamp.timezone,
                self.timestamp.custom_format,
                bad_rows,
            )

        return parsed

    def utc_to_string(self, dt: Union[datetime, pd.Timestamp]) -> str:
        """
        Convert a UTC datetime or pd.Timestamp to a custom string format.

        Some external APIs are picky about their timestamp formats, so we need the ability to pull a
        UTC timestamp from HydroServer and format it into a custom string.
        """
        if isinstance(dt, pd.Timestamp):
            dt = dt.to_pydatetime()

        tz_format = self.timestamp.format.lower()
        if tz_format == "iso8601":
            return dt.astimezone(timezone.utc).isoformat()

        if tz_format == "naive":
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        if tz_format == "custom":
            logger.debug(
                "Formatting runtime timestamp using custom format (customFormat=%r, timezoneMode=%r, timezone=%r).",
                self.timestamp.custom_format,
                self.timestamp.timezone_mode,
                self.timestamp.timezone,
            )
            return dt.astimezone(self.tz).strftime(self.timestamp.custom_format)

        raise ValueError(f"Unknown timestamp.format: {self.timestamp.format!r}")
