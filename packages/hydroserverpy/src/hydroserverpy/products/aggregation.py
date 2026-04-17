import logging
import polars as pl

from datetime import datetime, timezone
from typing import Literal

from pydantic import ConfigDict, validate_call

from hydroserverpy.core.duration import Duration, duration_to_us
from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, validate_timeseries, normalize_tz


logger = logging.getLogger(__name__)


_METHOD_EXPR = {
    "min": pl.col(RESULT_COL).min(),
    "max": pl.col(RESULT_COL).max(),
    "sum": pl.col(RESULT_COL).sum(),
    "mean": pl.col(RESULT_COL).mean(),
    "first": pl.col(RESULT_COL).first(),
    "last": pl.col(RESULT_COL).last(),
}


@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def apply_aggregation(
    df: pl.DataFrame,
    *,
    interval: Duration,
    method: Literal["min", "max", "sum", "mean", "first", "last"],
    anchor: datetime | None = None,
    local_timezone: str | None = None,
    min_values: int | None = None,
    on_sparse: Literal["drop", "raise", "stop"] = "drop",
    no_data_value: float | None = None,
) -> pl.DataFrame:
    """
    Aggregate a timeseries DataFrame into fixed-duration windows.

    Each output row represents one window, timestamped at the window start.
    When a window has fewer than min_values observations, on_sparse controls how the
    window is handled: 'drop' omits the window, 'raise' raises a ValueError, and
    'stop' returns windows up to the first window that doesn't meet the threshold.
    """

    validate_timeseries(df)

    input_rows = df.height
    logger.debug(
        "Aggregating %d row(s) (interval=%r, method=%r, minValues=%r, onSparse=%r, noDataValue=%r).",
        input_rows, interval, method, min_values, on_sparse, no_data_value,
    )

    if no_data_value is not None:
        df = df.filter(pl.col(RESULT_COL) != no_data_value)
        dropped = input_rows - df.height
        if dropped:
            logger.debug("Dropped %d no-data row(s) (noDataValue=%r).", dropped, no_data_value)

    if min_values is not None and min_values < 1:
        raise ValueError("min_values must be at least 1.")

    if on_sparse != "drop" and min_values is None:
        raise ValueError("on_sparse requires min_values to be set.")

    # Convert to a local timezone before grouping so window boundaries align
    # to local calendar time rather than UTC. Reverted to UTC after aggregation.
    tz_str = normalize_tz(local_timezone) if local_timezone else "UTC"
    localized_df = df.with_columns(
        pl.col(TIMESTAMP_COL).dt.convert_time_zone(tz_str)
    )

    # Compute the offset to pass to group_by_dynamic. Polars aligns windows to
    # the UTC epoch by default; the offset shifts boundaries to match the anchor.
    # offset = (anchor - epoch) mod interval, expressed as a duration string.
    if anchor is not None:
        anchor_utc = (
            anchor if anchor.tzinfo is not None
            else anchor.replace(tzinfo=timezone.utc)
        )
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        interval_us = duration_to_us(interval)
        anchor_us = int((anchor_utc - epoch).total_seconds() * 1_000_000)
        offset_us = anchor_us % interval_us
        offset = f"{offset_us}us"
    else:
        offset = "0us"

    aggregated_df = (
        localized_df.sort(TIMESTAMP_COL)
        .group_by_dynamic(
            TIMESTAMP_COL,
            every=interval,
            offset=offset,
            closed="left",
            label="left",
        )
        .agg(
            _METHOD_EXPR[method].alias(RESULT_COL),
            pl.col(RESULT_COL).count().alias("_count"),
        )
    )

    # Handle windows that don't meet the minimum observation threshold.
    if min_values is not None:
        if on_sparse == "raise":
            if aggregated_df.filter(pl.col("_count") < min_values).height > 0:
                raise ValueError(
                    f"One or more aggregation windows have fewer than {min_values} observations."
                )

        elif on_sparse == "stop":
            # Truncate at the first window that doesn't meet the threshold.
            sparse_rows = aggregated_df.with_row_index("_idx").filter(pl.col("_count") < min_values)
            if sparse_rows.height > 0:
                aggregated_df = aggregated_df.slice(0, sparse_rows[0, "_idx"])

        else:  # "drop"
            aggregated_df = aggregated_df.filter(pl.col("_count") >= min_values)

    result = (
        aggregated_df
        .drop("_count")
        .with_columns(
            pl.col(TIMESTAMP_COL).dt.convert_time_zone("UTC").dt.cast_time_unit("us")
        )
        .select([TIMESTAMP_COL, RESULT_COL])
        .sort(TIMESTAMP_COL)
    )

    logger.info("Aggregation produced %d window(s) from %d input row(s).", result.height, input_rows)

    return result
