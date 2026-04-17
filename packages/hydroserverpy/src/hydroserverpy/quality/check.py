import logging
import polars as pl

from datetime import timedelta
from pydantic import ConfigDict, validate_call

from hydroserverpy.core.duration import Duration, duration_to_us
from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, validate_timeseries, accept_pandas


logger = logging.getLogger(__name__)


@accept_pandas
@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def check_range(
    df: pl.DataFrame,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
    no_data_value: float | None = None,
) -> dict:
    """
    Identify observations that fall outside the allowed [min_value, max_value] range.

    At least one bound must be provided. Bounds are inclusive.
    """

    validate_timeseries(df)

    if min_value is None and max_value is None:
        raise ValueError("At least one of min_value or max_value must be provided.")

    if min_value is not None and max_value is not None and min_value >= max_value:
        raise ValueError("min_value must be less than max_value.")

    if no_data_value is not None:
        df = df.filter(pl.col(RESULT_COL) != no_data_value)

    logger.debug(
        "Running range check on %d row(s) (minValue=%r, maxValue=%r, noDataValue=%r).",
        df.height, min_value, max_value, no_data_value,
    )

    mask = pl.lit(False)
    if min_value is not None:
        mask = mask | (pl.col(RESULT_COL) < min_value)
    if max_value is not None:
        mask = mask | (pl.col(RESULT_COL) > max_value)

    violations = df.filter(mask)

    logger.info(
        "Range check found %d violation(s) in %d row(s).",
        violations.height, df.height,
    )

    return {
        "violation_count": violations.height,
        "timestamps": violations[TIMESTAMP_COL].to_list(),
        "values": violations[RESULT_COL].to_list(),
    }


@accept_pandas
@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def check_rate_of_change(
    df: pl.DataFrame,
    *,
    window: Duration,
    max_change: float,
    no_data_value: float | None = None,
) -> dict:
    """
    Identify observations where the absolute change over the preceding window exceeds max_change.

    For each observation T where at least one full window of data precedes it, the check compares
    T's value to the most recent observation at or before T - window. Observations in the first
    window of the series are skipped, as are observations with no reference found before T - window
    (i.e., the preceding observation fell in a gap).

    When the window matches the series' intended time spacing, each observation is effectively
    compared to its immediate predecessor.
    """

    validate_timeseries(df)

    if no_data_value is not None:
        df = df.filter(pl.col(RESULT_COL) != no_data_value)

    window_us = duration_to_us(window)

    logger.debug(
        "Running rate-of-change check on %d row(s) (window=%r, maxChange=%r, noDataValue=%r).",
        df.height, window, max_change, no_data_value,
    )

    df_sorted = df.sort(TIMESTAMP_COL)
    first_ts = df_sorted[TIMESTAMP_COL].min()

    if first_ts is None:
        return {"violation_count": 0, "timestamps": [], "changes": []}

    start_threshold = first_ts + timedelta(microseconds=window_us)

    df_ref = df_sorted.select([
        pl.col(TIMESTAMP_COL).alias("_ref_ts"),
        pl.col(RESULT_COL).alias("_prev_result"),
    ])

    eligible = (
        df_sorted
        .filter(pl.col(TIMESTAMP_COL) >= start_threshold)
        .with_columns(
            (pl.col(TIMESTAMP_COL) - pl.duration(microseconds=window_us)).alias("_lookback_ts")
        )
        .join_asof(df_ref, left_on="_lookback_ts", right_on="_ref_ts", strategy="backward")
        .drop("_lookback_ts")
        .filter(pl.col("_prev_result").is_not_null())
    )

    if eligible.is_empty():
        logger.info("Rate-of-change check: no eligible observations, 0 violations.")
        return {"violation_count": 0, "timestamps": [], "changes": []}

    violations = eligible.filter(
        (pl.col(RESULT_COL) - pl.col("_prev_result")).abs() > max_change
    ).with_columns(
        (pl.col(RESULT_COL) - pl.col("_prev_result")).abs().alias("_change")
    )

    logger.info(
        "Rate-of-change check found %d violation(s) in %d eligible row(s).",
        violations.height, eligible.height,
    )

    return {
        "violation_count": violations.height,
        "timestamps": violations[TIMESTAMP_COL].to_list(),
        "changes": violations["_change"].to_list(),
    }


@accept_pandas
@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def check_persistence(
    df: pl.DataFrame,
    *,
    window: Duration,
    min_value: float | None = None,
    max_value: float | None = None,
    no_data_value: float | None = None,
) -> dict:
    """
    Identify observations where the value has not changed over the preceding window.

    For each observation T where at least one full window of data precedes it, the check tests
    whether the rolling min and max over [T - window, T] are equal. If min_value and/or max_value
    are provided, only stuck values within that range are flagged — useful for detecting sensors
    frozen at a suspicious value rather than legitimately constant readings.
    """

    validate_timeseries(df)

    if no_data_value is not None:
        df = df.filter(pl.col(RESULT_COL) != no_data_value)

    window_us = duration_to_us(window)

    logger.debug(
        "Running persistence check on %d row(s) (window=%r, minValue=%r, maxValue=%r, noDataValue=%r).",
        df.height, window, min_value, max_value, no_data_value,
    )

    df_sorted = df.sort(TIMESTAMP_COL)
    first_ts = df_sorted[TIMESTAMP_COL].min()

    if first_ts is None:
        return {"violation_count": 0, "timestamps": [], "values": []}

    start_threshold = first_ts + timedelta(microseconds=window_us)

    df_rolling = df_sorted.with_columns([
        pl.col(RESULT_COL).rolling_min_by(TIMESTAMP_COL, window_size=window, closed="both").alias("_rolling_min"),
        pl.col(RESULT_COL).rolling_max_by(TIMESTAMP_COL, window_size=window, closed="both").alias("_rolling_max"),
    ])

    mask = (
        (pl.col(TIMESTAMP_COL) >= start_threshold) &
        (pl.col("_rolling_min") == pl.col("_rolling_max"))
    )

    if min_value is not None:
        mask = mask & (pl.col(RESULT_COL) >= min_value)
    if max_value is not None:
        mask = mask & (pl.col(RESULT_COL) <= max_value)

    violations = df_rolling.filter(mask)

    logger.info(
        "Persistence check found %d violation(s) in %d row(s).",
        violations.height, df.height,
    )

    return {
        "violation_count": violations.height,
        "timestamps": violations[TIMESTAMP_COL].to_list(),
        "values": violations[RESULT_COL].to_list(),
    }
