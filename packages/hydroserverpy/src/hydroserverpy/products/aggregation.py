import logging
import pandas as pd

from datetime import datetime, timezone
from typing import Literal

from pydantic import ConfigDict, validate_call

from hydroserverpy.core.duration import Duration, duration_to_us
from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, validate_timeseries, normalize_tz


logger = logging.getLogger(__name__)


@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def apply_aggregation(
    df: pd.DataFrame,
    *,
    interval: Duration,
    method: Literal["min", "max", "sum", "mean", "first", "last"],
    anchor: datetime | None = None,
    local_timezone: str | None = None,
    min_values: int | None = None,
    on_sparse: Literal["drop", "raise", "stop"] = "drop",
    no_data_value: float | None = None,
) -> pd.DataFrame:
    """
    Aggregate a timeseries DataFrame into fixed-duration windows.

    Each output row represents one window, timestamped at the window start.
    When a window has fewer than min_values observations, on_sparse controls how the
    window is handled: 'drop' omits the window, 'raise' raises a ValueError, and
    'stop' returns windows up to the first window that doesn't meet the threshold.
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

    if on_sparse != "drop" and min_values is None:
        raise ValueError("on_sparse requires min_values to be set.")

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

    resampled = (
        localized
        .sort_values(TIMESTAMP_COL)
        .resample(rule=freq, on=TIMESTAMP_COL, closed="left", label="left", offset=offset)
    )

    aggregated = pd.DataFrame({
        RESULT_COL: getattr(resampled[RESULT_COL], method)(),
        "_count": resampled[RESULT_COL].count(),
    })

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

        else:  # "drop"
            aggregated = aggregated[~sparse_mask]

    result = aggregated.drop(columns=["_count"]).reset_index()
    result[TIMESTAMP_COL] = result[TIMESTAMP_COL].dt.tz_convert("UTC").dt.as_unit("us")
    result = result.sort_values(TIMESTAMP_COL).reset_index(drop=True)

    logger.info("Aggregation produced %d window(s) from %d input row(s).", len(result), input_rows)

    return result