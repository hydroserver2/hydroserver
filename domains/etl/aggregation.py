from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone as dt_timezone, tzinfo
import math
import re
from bisect import bisect_left
from typing import Iterable
from zoneinfo import ZoneInfo


AGGREGATION_STATISTICS = {
    "simple_mean",
    "time_weighted_daily_mean",
    "last_value_of_day",
}
AGGREGATION_TIMEZONE_MODES = {"fixedOffset", "daylightSavings"}
_FIXED_OFFSET_RE = re.compile(r"^([+-])(\d{2})(\d{2})$")


@dataclass(frozen=True)
class AggregationTransformation:
    aggregation_statistic: str
    timezone_mode: str
    timezone: str


def _first_non_empty(mapping: dict, keys: Iterable[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        return value
    return None


def _parse_fixed_offset(offset: str) -> tzinfo:
    match = _FIXED_OFFSET_RE.fullmatch(offset)
    if not match:
        raise ValueError("fixedOffset timezone must match +/-HHMM")

    sign, hours_raw, minutes_raw = match.groups()
    hours = int(hours_raw)
    minutes = int(minutes_raw)
    if minutes >= 60:
        raise ValueError("fixedOffset timezone minutes must be between 00 and 59")

    offset_delta = timedelta(hours=hours, minutes=minutes)
    if sign == "-":
        offset_delta = -offset_delta

    return dt_timezone(offset_delta)


def timezone_info_for_transformation(transform: AggregationTransformation) -> tzinfo:
    if transform.timezone_mode == "fixedOffset":
        return _parse_fixed_offset(transform.timezone)

    if transform.timezone_mode == "daylightSavings":
        try:
            return ZoneInfo(transform.timezone)
        except Exception as exc:  # pragma: no cover - platform-specific internals
            raise ValueError(
                "daylightSavings timezone must be a valid IANA timezone"
            ) from exc

    raise ValueError(f"Unsupported timezoneMode: {transform.timezone_mode}")


def normalize_aggregation_transformation(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Aggregation transformation must be an object")

    transform_type = raw.get("type")
    if transform_type != "aggregation":
        raise ValueError("Aggregation transformation must set type='aggregation'")

    aggregation_statistic = _first_non_empty(
        raw, ("aggregationStatistic", "aggregation_statistic")
    )
    if not isinstance(aggregation_statistic, str) or aggregation_statistic not in AGGREGATION_STATISTICS:
        allowed = ", ".join(sorted(AGGREGATION_STATISTICS))
        raise ValueError(f"aggregationStatistic must be one of: {allowed}")

    timezone_mode = _first_non_empty(raw, ("timezoneMode", "timezone_mode"))
    if not isinstance(timezone_mode, str) or timezone_mode not in AGGREGATION_TIMEZONE_MODES:
        allowed = ", ".join(sorted(AGGREGATION_TIMEZONE_MODES))
        raise ValueError(f"timezoneMode must be one of: {allowed}")

    timezone_value = _first_non_empty(raw, ("timezone",))
    if not isinstance(timezone_value, str):
        raise ValueError("timezone is required for aggregation transformations")

    normalized = {
        "type": "aggregation",
        "aggregationStatistic": aggregation_statistic,
        "timezoneMode": timezone_mode,
        "timezone": timezone_value,
    }

    # Validate timezone now so malformed configs fail early.
    timezone_info_for_transformation(
        AggregationTransformation(
            aggregation_statistic=aggregation_statistic,
            timezone_mode=timezone_mode,
            timezone=timezone_value,
        )
    )

    return normalized


def parse_aggregation_transformation(raw: dict) -> AggregationTransformation:
    normalized = normalize_aggregation_transformation(raw)
    return AggregationTransformation(
        aggregation_statistic=normalized["aggregationStatistic"],
        timezone_mode=normalized["timezoneMode"],
        timezone=normalized["timezone"],
    )


def _local_midnight(timestamp_utc: datetime, tz: tzinfo) -> datetime:
    local = timestamp_utc.astimezone(tz)
    return datetime.combine(local.date(), time.min, tzinfo=tz)


def closed_window_end_utc(source_end_utc: datetime, transform: AggregationTransformation) -> datetime:
    tz = timezone_info_for_transformation(transform)
    return _local_midnight(source_end_utc, tz).astimezone(dt_timezone.utc)


def first_window_start_utc(source_begin_utc: datetime, transform: AggregationTransformation) -> datetime:
    tz = timezone_info_for_transformation(transform)
    return _local_midnight(source_begin_utc, tz).astimezone(dt_timezone.utc)


def next_window_start_utc(destination_end_utc: datetime, transform: AggregationTransformation) -> datetime:
    tz = timezone_info_for_transformation(transform)
    destination_local = destination_end_utc.astimezone(tz)
    next_date = destination_local.date() + timedelta(days=1)
    local_midnight = datetime.combine(next_date, time.min, tzinfo=tz)
    return local_midnight.astimezone(dt_timezone.utc)


def iter_daily_windows_utc(
    start_utc: datetime,
    end_utc: datetime,
    transform: AggregationTransformation,
):
    tz = timezone_info_for_transformation(transform)

    current_local = _local_midnight(start_utc, tz)
    end_local = _local_midnight(end_utc, tz)

    while current_local < end_local:
        next_local = datetime.combine(
            current_local.date() + timedelta(days=1),
            time.min,
            tzinfo=tz,
        )
        yield (
            current_local.astimezone(dt_timezone.utc),
            next_local.astimezone(dt_timezone.utc),
            current_local.date(),
        )
        current_local = next_local


def _boundary_value(
    target: datetime,
    timestamps: list[datetime],
    values: list[float],
    prev_idx: int | None,
    next_idx: int | None,
) -> float | None:
    prev = None
    nxt = None

    if prev_idx is not None and 0 <= prev_idx < len(timestamps):
        prev = (timestamps[prev_idx], values[prev_idx])
    if next_idx is not None and 0 <= next_idx < len(timestamps):
        nxt = (timestamps[next_idx], values[next_idx])

    if prev and prev[0] == target:
        return prev[1]
    if nxt and nxt[0] == target:
        return nxt[1]

    if prev and nxt:
        t0, v0 = prev
        t1, v1 = nxt
        span = (t1 - t0).total_seconds()
        if span <= 0:
            return v1
        ratio = (target - t0).total_seconds() / span
        return v0 + ratio * (v1 - v0)

    if prev:
        return prev[1]
    if nxt:
        return nxt[1]

    return None


def aggregate_daily_window(
    timestamps: list[datetime],
    values: list[float],
    window_start_utc: datetime,
    window_end_utc: datetime,
    statistic: str,
) -> float | None:
    if statistic not in AGGREGATION_STATISTICS:
        raise ValueError(f"Unsupported aggregationStatistic '{statistic}'")

    if not timestamps or len(timestamps) != len(values):
        return None

    if window_end_utc <= window_start_utc:
        return None

    left = bisect_left(timestamps, window_start_utc)
    right = bisect_left(timestamps, window_end_utc)

    # No observations in this day -> skip writing this day.
    if left == right:
        return None

    window_values = values[left:right]

    if statistic == "simple_mean":
        return sum(window_values) / len(window_values)

    if statistic == "last_value_of_day":
        return window_values[-1]

    # Time-weighted daily mean using trapezoidal integration over the daily window.
    start_value = _boundary_value(
        target=window_start_utc,
        timestamps=timestamps,
        values=values,
        prev_idx=(left - 1) if left > 0 else None,
        next_idx=left,
    )
    end_value = _boundary_value(
        target=window_end_utc,
        timestamps=timestamps,
        values=values,
        prev_idx=(right - 1) if right > 0 else None,
        next_idx=right if right < len(timestamps) else None,
    )

    if start_value is None or end_value is None:
        return None

    area_points: list[tuple[datetime, float]] = [(window_start_utc, start_value)]
    for idx in range(left, right):
        ts = timestamps[idx]
        val = values[idx]
        if ts == window_start_utc:
            area_points[0] = (ts, val)
            continue
        area_points.append((ts, val))

    if area_points[-1][0] == window_end_utc:
        area_points[-1] = (window_end_utc, end_value)
    else:
        area_points.append((window_end_utc, end_value))

    total_area = 0.0
    for idx in range(1, len(area_points)):
        t0, v0 = area_points[idx - 1]
        t1, v1 = area_points[idx]
        span = (t1 - t0).total_seconds()
        if span <= 0:
            continue
        total_area += (v0 + v1) * 0.5 * span

    duration = (window_end_utc - window_start_utc).total_seconds()
    if duration <= 0:
        return None

    result = total_area / duration
    if math.isnan(result) or math.isinf(result):
        return None

    return result
