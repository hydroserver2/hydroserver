import logging
import pandas as pd

from datetime import timedelta
from pydantic import ConfigDict, validate_call

from hydroserverpy.core.duration import Duration, duration_to_us
from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, validate_timeseries


logger = logging.getLogger(__name__)


@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def check_range(
    df: pd.DataFrame,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
    no_data_value: float | None = None,
) -> dict:
    """
    Identify observations that fall outside the allowed [min_value, max_value] range.

    At least one bound must be provided. Bounds are inclusive.
    """

    df = validate_timeseries(df)

    if min_value is None and max_value is None:
        raise ValueError("At least one of min_value or max_value must be provided.")

    if min_value is not None and max_value is not None and min_value >= max_value:
        raise ValueError("min_value must be less than max_value.")

    if no_data_value is not None:
        df = df[df[RESULT_COL] != no_data_value].reset_index(drop=True)

    logger.debug(
        "Running range check on %d row(s) (minValue=%r, maxValue=%r, noDataValue=%r).",
        len(df), min_value, max_value, no_data_value,
    )

    mask = pd.Series(False, index=df.index)
    if min_value is not None:
        mask = mask | (df[RESULT_COL] < min_value)
    if max_value is not None:
        mask = mask | (df[RESULT_COL] > max_value)

    violations = df[mask]

    logger.info(
        "Range check found %d violation(s) in %d row(s).",
        len(violations), len(df),
    )

    return {
        "violation_count": len(violations),
        "timestamps": violations[TIMESTAMP_COL].tolist(),
        "values": violations[RESULT_COL].tolist(),
    }


@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def check_rate_of_change(
    df: pd.DataFrame,
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

    df = validate_timeseries(df)

    if no_data_value is not None:
        df = df[df[RESULT_COL] != no_data_value].reset_index(drop=True)

    window_us = duration_to_us(window)

    logger.debug(
        "Running rate-of-change check on %d row(s) (window=%r, maxChange=%r, noDataValue=%r).",
        len(df), window, max_change, no_data_value,
    )

    df_sorted = df.sort_values(TIMESTAMP_COL).reset_index(drop=True)
    first_ts = df_sorted[TIMESTAMP_COL].min()

    if pd.isna(first_ts):
        return {"violation_count": 0, "timestamps": [], "changes": []}

    start_threshold = first_ts + timedelta(microseconds=window_us)

    df_ref = df_sorted[[TIMESTAMP_COL, RESULT_COL]].rename(
        columns={TIMESTAMP_COL: "_ref_ts", RESULT_COL: "_prev_result"}
    )

    eligible = df_sorted[df_sorted[TIMESTAMP_COL] >= start_threshold].copy()
    eligible["_lookback_ts"] = (eligible[TIMESTAMP_COL] - pd.Timedelta(microseconds=window_us)).dt.as_unit("us")

    eligible = pd.merge_asof(
        eligible.sort_values("_lookback_ts"),
        df_ref.sort_values("_ref_ts"),
        left_on="_lookback_ts",
        right_on="_ref_ts",
        direction="backward",
    ).drop(columns=["_lookback_ts", "_ref_ts"])

    eligible = eligible[eligible["_prev_result"].notna()].reset_index(drop=True)

    if len(eligible) == 0:
        logger.info("Rate-of-change check: no eligible observations, 0 violations.")
        return {"violation_count": 0, "timestamps": [], "changes": []}

    eligible["_change"] = (eligible[RESULT_COL] - eligible["_prev_result"]).abs()
    violations = eligible[eligible["_change"] > max_change]

    logger.info(
        "Rate-of-change check found %d violation(s) in %d eligible row(s).",
        len(violations), len(eligible),
    )

    return {
        "violation_count": len(violations),
        "timestamps": violations[TIMESTAMP_COL].tolist(),
        "changes": violations["_change"].tolist(),
    }


@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def check_persistence(
    df: pd.DataFrame,
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

    df = validate_timeseries(df)

    if no_data_value is not None:
        df = df[df[RESULT_COL] != no_data_value].reset_index(drop=True)

    window_us = duration_to_us(window)

    logger.debug(
        "Running persistence check on %d row(s) (window=%r, minValue=%r, maxValue=%r, noDataValue=%r).",
        len(df), window, min_value, max_value, no_data_value,
    )

    df_sorted = df.sort_values(TIMESTAMP_COL).reset_index(drop=True)
    first_ts = df_sorted[TIMESTAMP_COL].min()

    if pd.isna(first_ts):
        return {"violation_count": 0, "timestamps": [], "values": []}

    start_threshold = first_ts + timedelta(microseconds=window_us)

    window_td = pd.Timedelta(microseconds=window_us)
    rolling = df_sorted.rolling(window=window_td, on=TIMESTAMP_COL, closed="both")
    df_sorted = df_sorted.copy()
    df_sorted["_rolling_min"] = rolling[RESULT_COL].min()
    df_sorted["_rolling_max"] = rolling[RESULT_COL].max()

    mask = (
        (df_sorted[TIMESTAMP_COL] >= start_threshold) &
        (df_sorted["_rolling_min"] == df_sorted["_rolling_max"])
    )

    if min_value is not None:
        mask = mask & (df_sorted[RESULT_COL] >= min_value)
    if max_value is not None:
        mask = mask & (df_sorted[RESULT_COL] <= max_value)

    violations = df_sorted[mask]

    logger.info(
        "Persistence check found %d violation(s) in %d row(s).",
        len(violations), len(df),
    )

    return {
        "violation_count": len(violations),
        "timestamps": violations[TIMESTAMP_COL].tolist(),
        "values": violations[RESULT_COL].tolist(),
    }
