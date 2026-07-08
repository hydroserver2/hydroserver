import re
import pandas as pd
from datetime import datetime, timezone, timedelta, tzinfo
from zoneinfo import ZoneInfo
from typing import Literal, Optional
from pydantic import BaseModel, model_validator
from functools import cached_property


TimestampType = Literal["iso", "custom"]
TimezoneType = Literal["utc", "offset", "iana"]

_OFFSET_RE = re.compile(r"^[+-](\d{4}|\d{2}:\d{2})$")


class Timezone(BaseModel):
    timezone_type: Optional[TimezoneType] = None
    timezone: Optional[str] = None

    @model_validator(mode="after")
    def validate_timezone(self) -> "Timezone":
        if self.timezone_type in {"offset", "iana"} and not self.timezone:
            raise ValueError(
                "Invalid timezone configuration. "
                "Timezone offset must be provided when using IANA or UTC offsets"
            )
        elif self.timezone_type == "offset":
            self._validate_utc_offset(self.timezone)
        elif self.timezone_type == "iana":
            try:
                ZoneInfo(self.timezone)
            except Exception:
                raise ValueError(
                    f"Invalid IANA timezone '{self.timezone}' "
                    "(example: 'America/Denver')."
                )
        elif self.timezone_type is None and self.timezone is not None:
            raise ValueError(
                "Invalid timezone configuration. "
                "Default timezone value must not be provided when the "
                "timezone is expected to be embedded in the timestamp values."
            )

        return self

    @classmethod
    def _validate_utc_offset(cls, value: str) -> None:
        if not _OFFSET_RE.match(value):
            raise ValueError(
                f"Invalid timestamp UTC offset '{value}'. "
                "UTC offsets must be specified in ±HHMM or ±HH:MM format (e.g: '-0700' or '-07:00') "
                "with hours between 00 and 14 and minutes between 00 and 59."
            )

        clean = value.replace(":", "")
        hours = int(clean[1:3])
        minutes = int(clean[3:5])

        if hours > 14 or minutes >= 60 or (hours == 14 and minutes != 0):
            raise ValueError(
                f"Invalid timestamp UTC offset '{value}'. "
                "UTC offsets must be specified in ±HHMM or ±HH:MM format (e.g: '-0700' or '-07:00') "
                "with hours between 00 and 14 and minutes between 00 and 59."
            )

    @staticmethod
    def _to_pandas_offset(value: str) -> str:
        """
        Normalise a UTC offset string to the ±HH:MM format required by pandas tz_localize.
        Accepts both ±HHMM and ±HH:MM as input.
        """

        if ":" in value:
            return value
        return f"{value[0]}{value[1:3]}:{value[3:5]}"

    @cached_property
    def tz(self) -> Optional[tzinfo]:
        """
        Return the configured timezone as a datetime.tzinfo instance.
        """

        if self.timezone_type == "offset":
            sign = 1 if self.timezone[0] == "+" else -1
            clean = self.timezone.replace(":", "")
            minutes = int(clean[1:3]) * 60 + int(clean[3:5])
            return timezone(timedelta(minutes=sign * minutes))
        elif self.timezone_type == "iana":
            return ZoneInfo(self.timezone)
        elif self.timezone_type == "utc":
            return timezone.utc
        else:
            return None


class Timestamp(Timezone):
    timestamp_type: TimestampType = "iso"
    timestamp_format: Optional[str] = None

    @model_validator(mode="after")
    def validate_timestamp_format(self) -> "Timestamp":
        if self.timestamp_type == "custom" and not self.timestamp_format:
            raise ValueError(
                "Invalid timestamp configuration. "
                "Timestamp format is required when the timestamp type is 'custom'."
            )
        elif self.timestamp_type != "custom" and self.timestamp_format:
            raise ValueError(
                "Invalid timestamp configuration. "
                "Timestamp formats may only be used when the timestamp type is 'custom'"
            )
        elif self.timestamp_type == "custom" and self.timestamp_format:
            self._validate_strftime_format(self.timestamp_format)

        return self

    @classmethod
    def _validate_strftime_format(cls, value: str) -> None:
        try:
            datetime(2000, 1, 1, 0, 0, 0).strftime(value)
        except Exception as e:
            raise ValueError(
                f"Invalid timestamp format string {value!r}. "
                "Ensure the string uses valid strftime directives "
                "(e.g., '%Y-%m-%d %H:%M:%S')."
            ) from e

    def parse_series_to_utc(
        self,
        series: pd.Series
    ) -> pd.Series:
        """
        Parse a pandas Series of timestamps and normalize them to UTC.

        Accepts uniform datetime64 Series, object-dtype Series of ISO strings,
        object-dtype Series of strings with a custom timestamp_format, or
        object-dtype Series of pd.Timestamp/datetime objects. Raises ValueError
        on null values, mixed element types, or unsupported element types. Invalid
        strings raise during parsing. The returned Series is always
        datetime64[ns, UTC] with the same length as the input.

        For tz-naive inputs, the configured timezone is applied before converting
        to UTC. If no timezone is configured, UTC is assumed. Tz-aware inputs are
        converted to UTC from their embedded timezone without being overwritten.

        For custom timestamp formats: include %z in timestamp_format if strings
        carry embedded timezone info; omit %z if strings are tz-naive. A mismatch
        between the format and the actual strings raises during parsing.
        """

        if len(series) == 0:
            return pd.Series(dtype="datetime64[ns, UTC]")

        if series.isna().any():
            raise ValueError("Series contains null or missing values")

        tz_label = (
            self._to_pandas_offset(self.timezone) if self.timezone_type == "offset"
            else (self.timezone or "UTC")
        )

        # Uniform datetime64 (all naive or all same-tz-aware)
        if pd.api.types.is_datetime64_any_dtype(series):
            if series.dt.tz is None:
                return series.dt.tz_localize(
                    tz_label, ambiguous=False, nonexistent="shift_forward"
                ).dt.tz_convert("UTC")
            return series.dt.tz_convert("UTC")

        # Object dtype: must be uniformly strings or Timestamp/datetime objects
        first_timestamp = series.iloc[0]

        if isinstance(first_timestamp, str):
            series = series.str.strip()
            if series.isna().any():
                raise ValueError("Series contains mixed or non-string values")

            if self.timestamp_format:
                if "%z" in self.timestamp_format:
                    return pd.Series(
                        pd.to_datetime(series, utc=True, format=self.timestamp_format, errors="raise")
                    )
                return pd.Series(
                    pd.to_datetime(series, utc=False, format=self.timestamp_format, errors="raise")
                    .dt.tz_localize(tz_label, ambiguous=False, nonexistent="shift_forward")
                    .dt.tz_convert("UTC")
                )

            # ISO strings: regex detects embedded tz per element to support mixed-offset series
            # (pandas cannot parse mixed tz/naive strings without coercing to NaT)
            has_tz = series.str.contains(r"[Zz]$|[+-]\d{2}(?::?\d{2})?$", regex=True, na=False)
            tz_aware = pd.to_datetime(series[has_tz], utc=True, errors="raise")
            tz_naive_raw_series = pd.to_datetime(series[~has_tz], utc=False, errors="raise")

        elif isinstance(first_timestamp, pd.Timestamp):
            has_tz = series.apply(lambda x: x.tzinfo is not None)
            tz_aware = pd.to_datetime(series[has_tz], utc=True)
            tz_naive_raw_series = pd.to_datetime(series[~has_tz])

        else:
            raise ValueError(f"Unsupported series element type: {type(first_timestamp).__name__}")

        tz_naive_series = tz_naive_raw_series.dt.tz_localize(
            tz_label, ambiguous=False, nonexistent="shift_forward"
        ).dt.tz_convert("UTC")

        return pd.Series(pd.concat([tz_aware, tz_naive_series])).sort_index()

    def to_string(self, dt: datetime) -> str:
        """
        Convert a timezone-aware UTC datetime to a string using the configured
        timestamp type and timezone.

        For 'iso' timestamps, returns a standard ISO 8601 string in the
        configured timezone (or UTC if no timezone is set).

        For 'custom' timestamps, formats the datetime using timestamp_format
        in the configured timezone (or UTC if no timezone is set).
        """

        tz = self.tz or timezone.utc
        local_dt = dt.astimezone(tz)

        if self.timestamp_type == "custom":
            return local_dt.strftime(self.timestamp_format)

        if self.timezone_type is None:
            return local_dt.strftime("%Y-%m-%d %H:%M:%S")

        return local_dt.isoformat()
