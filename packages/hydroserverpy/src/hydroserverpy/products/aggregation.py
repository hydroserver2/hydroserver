import logging
import pandas as pd

from bisect import bisect_left
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from pydantic import ConfigDict, validate_call

from hydroserverpy.core.duration import Duration, duration_to_us
from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, validate_timeseries, normalize_tz


logger = logging.getLogger(__name__)

TIME_WEIGHTED_MEAN = "time_weighted_mean"

_DAY_US = 86_400_000_000
_DEFAULT_CALENDAR_ORIGIN = date(1970, 1, 5)


def _calendar_window_edges(timestamps: pd.Series, days: int, origin: date, tz: ZoneInfo) -> list:
    """
    Return the UTC edges of `days`-long local calendar windows covering `timestamps`.
    Windows start at local midnight on dates a whole number of windows from `origin`,
    so the grid doesn't depend on where the data starts. zoneinfo resolves nonexistent
    or ambiguous midnights (DST changing at 00:00) without raising, unlike pandas.
    """

    if len(timestamps) == 0:
        return []

    def midnight(day: date) -> datetime:
        return datetime.combine(day, time.min, tzinfo=tz).astimezone(timezone.utc)

    first_date = timestamps.iloc[0].tz_convert(tz).date()
    current = first_date - timedelta(days=(first_date - origin).days % days)
    edges = [midnight(current)]
    while edges[-1] <= timestamps.iloc[-1]:
        current += timedelta(days=days)
        edges.append(midnight(current))

    return edges


def _boundary_value(
    target: pd.Timestamp,
    timestamps: list,
    values: list,
    prev_idx: Optional[int],
    next_idx: Optional[int],
) -> Optional[float]:
    """
    Estimate the value at a window boundary by exact match or linear interpolation.

    If the observation immediately before (prev_idx) or after (next_idx) the boundary
    falls exactly on the target timestamp, that value is returned directly. Otherwise,
    if observations exist on both sides, the value is linearly interpolated. If only
    one side is available, that side's value is used as a flat extrapolation.
    """

    prev = None
    if prev_idx is not None and 0 <= prev_idx < len(timestamps):
        prev = (timestamps[prev_idx], values[prev_idx])

    nxt = None
    if next_idx is not None and 0 <= next_idx < len(timestamps):
        nxt = (timestamps[next_idx], values[next_idx])

    if prev is not None and prev[0] == target:
        return prev[1]
    if nxt is not None and nxt[0] == target:
        return nxt[1]

    if prev is not None and nxt is not None:
        t0, v0 = prev
        t1, v1 = nxt
        span = (t1 - t0).total_seconds()
        if span <= 0:
            return v1
        ratio = (target - t0).total_seconds() / span
        return v0 + ratio * (v1 - v0)

    if prev is not None:
        return prev[1]
    if nxt is not None:
        return nxt[1]

    return None


def _time_weighted_mean(localized: pd.DataFrame, windows: list) -> pd.Series:
    """
    Compute a trapezoidal (linear-interpolation) time-weighted mean for each
    (bin_start, bin_end) pair in `windows`.

    Each bin's value is the area under the piecewise-linear curve through the
    observations spanning [bin_start, bin_end), divided by the bin duration.
    Boundary values at the bin edges are estimated by linear interpolation between
    the nearest observations on each side, or a flat extrapolation if only one side
    has data. Bins with no observations are left as NaN (dropped later via _count).
    """

    timestamps = localized[TIMESTAMP_COL].tolist()
    values = localized[RESULT_COL].tolist()
    n = len(timestamps)

    results = []

    for window_start, window_end in windows:
        left = bisect_left(timestamps, window_start)
        right = bisect_left(timestamps, window_end)

        if left == right:
            results.append(float("nan"))
            continue

        start_value = _boundary_value(
            window_start, timestamps, values, left - 1 if left > 0 else None, left
        )
        end_value = _boundary_value(
            window_end, timestamps, values, right - 1, right if right < n else None
        )

        points = [(window_start, start_value)]
        for idx in range(left, right):
            ts, val = timestamps[idx], values[idx]
            if ts == window_start:
                points[0] = (ts, val)
            else:
                points.append((ts, val))

        if points[-1][0] == window_end:
            points[-1] = (window_end, end_value)
        else:
            points.append((window_end, end_value))

        area = 0.0
        for j in range(1, len(points)):
            t0, v0 = points[j - 1]
            t1, v1 = points[j]
            span = (t1 - t0).total_seconds()
            if span > 0:
                area += (v0 + v1) * 0.5 * span

        duration = (window_end - window_start).total_seconds()
        results.append(area / duration if duration > 0 else float("nan"))

    return pd.Series(results, index=pd.Index([start for start, _ in windows], name=TIMESTAMP_COL))


@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def apply_aggregation(
    df: pd.DataFrame,
    *,
    interval: Duration,
    method: Literal["min", "max", "sum", "mean", "first", "last", "time_weighted_mean"],
    anchor: datetime | None = None,
    local_timezone: str | None = None,
    min_values: int | None = None,
    on_sparse: Literal["drop", "raise", "stop", "ndv"] = "drop",
    no_data_value: float | None = None,
) -> pd.DataFrame:
    """
    Aggregate a timeseries DataFrame into fixed-duration windows.

    Each output row represents one window, timestamped at the window start.
    When a window has fewer than min_values observations, on_sparse controls how the
    window is handled: 'drop' omits the window, 'raise' raises a ValueError, 'stop'
    returns windows up to the first window that doesn't meet the threshold, and 'ndv'
    fills the window result with no_data_value (requires no_data_value to be set).

    'time_weighted_mean' differs from the other methods in that it weights each
    observation by the time it represents rather than treating all observations in
    a window equally, via trapezoidal integration between observations (interpolating
    across window boundaries as needed).

    Whole-day intervals (days, weeks) use local calendar days, so windows start at
    local midnight and follow DST (23/25-hour days). They're aligned to the local date
    of `anchor` (time of day ignored), or to Monday 1970-01-05, so the same windows
    result wherever the input starts.
    """

    df = validate_timeseries(df)

    input_rows = len(df)
    logger.debug(
        "Aggregating %d row(s) (interval=%r, method=%r, minValues=%r, onSparse=%r, noDataValue=%r).",
        input_rows, interval, method, min_values, on_sparse, no_data_value,
    )

    if no_data_value is not None:
        df = df[df[RESULT_COL] != no_data_value].reset_index(drop=True)
        dropped = input_rows - len(df)
        if dropped:
            logger.debug("Dropped %d no-data row(s) (noDataValue=%r).", dropped, no_data_value)

    if min_values is not None and min_values < 1:
        raise ValueError("min_values must be at least 1.")

    if on_sparse == "ndv" and no_data_value is None:
        raise ValueError("on_sparse='ndv' requires no_data_value to be set.")

    interval_us = duration_to_us(interval)
    freq = pd.Timedelta(microseconds=interval_us)

    # Compute resample offset to align windows to the anchor.
    # offset = (anchor - epoch) mod interval.
    if anchor is not None:
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        anchor_utc = anchor if anchor.tzinfo else anchor.replace(tzinfo=timezone.utc)
        anchor_us = int((anchor_utc - epoch).total_seconds() * 1_000_000)
        offset = pd.Timedelta(microseconds=anchor_us % interval_us)
    else:
        offset = pd.Timedelta(0)

    # Convert to local timezone before grouping so window boundaries align
    # to local calendar time rather than UTC. Reverted to UTC after aggregation.
    tz_str = normalize_tz(local_timezone) if local_timezone else "UTC"
    localized = df.copy()
    localized[TIMESTAMP_COL] = localized[TIMESTAMP_COL].dt.tz_convert(tz_str)
    localized = localized.sort_values(TIMESTAMP_COL).reset_index(drop=True)

    if interval_us % _DAY_US == 0:
        # Whole-day windows use explicit local-midnight edges instead of pandas'
        # resample, whose day bins start on the first observation's day (so they
        # shift with the input) and which raises on a nonexistent local midnight.
        tz = ZoneInfo(tz_str)
        origin = anchor_utc.astimezone(tz).date() if anchor is not None else _DEFAULT_CALENDAR_ORIGIN
        edges = pd.DatetimeIndex(
            _calendar_window_edges(localized[TIMESTAMP_COL], interval_us // _DAY_US, origin, tz), tz="UTC"
        ).tz_convert(tz_str)
        positions = edges.searchsorted(localized[TIMESTAMP_COL], side="right") - 1
        grouped = localized.groupby(edges[positions].rename(TIMESTAMP_COL))[RESULT_COL]
        counts = grouped.count()
        windows = [(edges[i], edges[i + 1]) for i in sorted(set(positions))]
    else:
        grouped = localized.resample(rule=freq, on=TIMESTAMP_COL, closed="left", label="left", offset=offset)[RESULT_COL]
        counts = grouped.count()
        windows = [(start, start + freq) for start in counts.index]

    if method == TIME_WEIGHTED_MEAN:
        values_col = _time_weighted_mean(localized, windows)
    else:
        values_col = getattr(grouped, method)()

    aggregated = pd.DataFrame({RESULT_COL: values_col, "_count": counts})

    # Drop empty bins (resample includes all bins in the range, even empty ones).
    aggregated = aggregated[aggregated["_count"] > 0]

    # Handle windows that don't meet the minimum observation threshold.
    if min_values is not None:
        sparse_mask = aggregated["_count"] < min_values

        if on_sparse == "raise":
            if sparse_mask.any():
                raise ValueError(
                    f"One or more aggregation windows have fewer than {min_values} observations."
                )

        elif on_sparse == "stop":
            if sparse_mask.any():
                first_sparse = int(sparse_mask.values.argmax())
                aggregated = aggregated.iloc[:first_sparse]

        elif on_sparse == "ndv":
            aggregated.loc[sparse_mask, RESULT_COL] = no_data_value

        else:  # "drop"
            aggregated = aggregated[~sparse_mask]

    result = aggregated.drop(columns=["_count"]).reset_index()
    result[TIMESTAMP_COL] = result[TIMESTAMP_COL].dt.tz_convert("UTC").dt.as_unit("us")
    result = result.sort_values(TIMESTAMP_COL).reset_index(drop=True)

    logger.info("Aggregation produced %d window(s) from %d input row(s).", len(result), input_rows)

    return result