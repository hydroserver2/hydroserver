import logging
import pandas as pd

from bisect import bisect_left
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import ConfigDict, validate_call

from hydroserverpy.core.duration import Duration, duration_to_us
from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, validate_timeseries, normalize_tz


logger = logging.getLogger(__name__)

TIME_WEIGHTED_MEAN = "time_weighted_mean"


def _resample(frame: pd.DataFrame, rule, offset: pd.Timedelta):
    """
    Resample `frame` on TIMESTAMP_COL, omitting `offset` for calendar-aware
    rules (e.g. Day) that don't support it — passing it anyway is harmless
    (those rules are only used when offset is the zero default) but pandas
    emits a RuntimeWarning on every call otherwise.
    """

    kwargs = dict(rule=rule, on=TIMESTAMP_COL, closed="left", label="left")
    if isinstance(rule, pd.Timedelta):
        kwargs["offset"] = offset
    return frame.resample(**kwargs)


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


def _next_bin_start(bin_start: pd.Timestamp, rule, offset: pd.Timedelta) -> pd.Timestamp:
    """
    Return the bin boundary immediately after `bin_start`, using pandas' own
    resample binning rather than direct date arithmetic.

    A plain `bin_start + rule` (or `pd.date_range`) can drift by the DST offset
    across a transition, and that behavior isn't consistent across pandas
    versions. Resampling a probe frame anchored at `bin_start` guarantees the
    next label is computed by the exact same binning algorithm already used
    (and proven correct) for every other bin boundary in the caller. `offset`
    only has an effect when `rule` is Tick-based (e.g. a Timedelta); it's
    ignored by pandas for calendar-aware offsets like Day, which is fine since
    those are only used when no anchor/offset was requested.
    """

    probe = pd.DataFrame({TIMESTAMP_COL: [bin_start, bin_start + 2 * rule]})
    edges = _resample(probe, rule, offset).size().index
    return edges[1]


def _time_weighted_mean(localized: pd.DataFrame, bin_starts: list, rule, offset: pd.Timedelta) -> pd.Series:
    """
    Compute a trapezoidal (linear-interpolation) time-weighted mean for each bin.

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

    for i, window_start in enumerate(bin_starts):
        if i + 1 < len(bin_starts):
            window_end = bin_starts[i + 1]
        else:
            # No trailing bin label for the last window.
            window_end = _next_bin_start(window_start, rule, offset)

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

    return pd.Series(results, index=pd.Index(bin_starts, name=TIMESTAMP_COL))


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

    # Day-or-longer intervals use a calendar-aware offset so windows respect
    # local wall-clock (DST) boundaries rather than a fixed absolute duration
    # (e.g. a "day" around a spring-forward transition is 23 real hours, not
    # 24). Tick-based rules like Timedelta can't express that, and pandas
    # ignores `offset=` for calendar-aware rules, so this only applies when
    # there's no anchor.
    _DAY_US = 86_400_000_000
    if anchor is None and interval_us % _DAY_US == 0:
        resample_rule = pd.tseries.offsets.Day(interval_us // _DAY_US)
    else:
        resample_rule = freq

    # Convert to local timezone before grouping so window boundaries align
    # to local calendar time rather than UTC. Reverted to UTC after aggregation.
    tz_str = normalize_tz(local_timezone) if local_timezone else "UTC"
    localized = df.copy()
    localized[TIMESTAMP_COL] = localized[TIMESTAMP_COL].dt.tz_convert(tz_str)
    localized = localized.sort_values(TIMESTAMP_COL).reset_index(drop=True)

    resampled = _resample(localized, resample_rule, offset)
    counts = resampled[RESULT_COL].count()

    if method == TIME_WEIGHTED_MEAN:
        values_col = _time_weighted_mean(localized, counts.index.tolist(), resample_rule, offset)
    else:
        values_col = getattr(resampled[RESULT_COL], method)()

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