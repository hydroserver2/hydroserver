import logging

import numpy as np
import pandas as pd

from typing import Literal
from pydantic import ConfigDict, validate_call

from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, validate_timeseries


logger = logging.getLogger(__name__)


@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def apply_rating_curve(
    df: pd.DataFrame,
    *,
    breakpoints: list[tuple[float, float]],
    method: Literal["linear", "power_law"] = "linear",
    out_of_range: Literal["drop", "raise", "stop", "ndv"] = "drop",
    no_data_value: float | None = None,
) -> pd.DataFrame:
    """
    Apply a rating curve to a stage timeseries to produce a discharge timeseries.

    Breakpoints define the curve as (stage, discharge) pairs. For 'linear', discharge
    is interpolated piecewise between adjacent breakpoints. For 'power_law', a curve
    of the form y = a·xᵇ is fitted to all breakpoints via log-log regression.

    The out_of_range input controls behavior when a stage value falls outside the breakpoint
    range (or is non-positive for power_law): 'drop' omits those rows, 'raise' raises
    a ValueError, 'stop' returns rows up to the first out-of-range value, and 'ndv'
    fills the result with no_data_value (requires no_data_value to be set).
    """

    df = validate_timeseries(df)

    input_rows = len(df)
    logger.debug(
        "Applying rating curve to %d row(s) (method=%r, breakpoints=%d, outOfRange=%r, noDataValue=%r).",
        input_rows, method, len(breakpoints), out_of_range, no_data_value,
    )

    if no_data_value is not None:
        df = df[df[RESULT_COL] != no_data_value].reset_index(drop=True)
        dropped = input_rows - len(df)
        if dropped:
            logger.debug("Dropped %d no-data row(s) (noDataValue=%r).", dropped, no_data_value)

    if out_of_range == "ndv" and no_data_value is None:
        raise ValueError("out_of_range='ndv' requires no_data_value to be set.")

    if len(breakpoints) < 2:
        raise ValueError("At least 2 breakpoints are required.")

    sorted_breakpoints = sorted(breakpoints, key=lambda p: p[0])
    xs = np.array([point[0] for point in sorted_breakpoints], dtype=np.float64)
    ys = np.array([point[1] for point in sorted_breakpoints], dtype=np.float64)

    if method == "power_law":
        if (xs <= 0).any() or (ys <= 0).any():
            raise ValueError("power_law requires all breakpoint values to be positive.")

    stage = df[RESULT_COL].to_numpy()

    # For power_law, non-positive stage values are also considered out-of-range.
    if method == "power_law":
        out_of_range_mask = (stage <= 0) | (stage < xs[0]) | (stage > xs[-1])
    else:
        out_of_range_mask = (stage < xs[0]) | (stage > xs[-1])

    if out_of_range == "raise":
        if out_of_range_mask.any():
            raise ValueError(
                "One or more stage values are outside the valid range for this rating curve."
            )

    elif out_of_range == "stop":
        first_out_of_range = int(np.argmax(out_of_range_mask)) if out_of_range_mask.any() else len(stage)
        df = df.iloc[:first_out_of_range].reset_index(drop=True)
        stage = stage[:first_out_of_range]
        out_of_range_mask = out_of_range_mask[:first_out_of_range]

    if method == "linear":
        result = np.interp(stage, xs, ys)

    else:  # power_law
        b, log_a = np.polyfit(np.log(xs), np.log(ys), 1)
        a = np.exp(log_a)

        with np.errstate(invalid="ignore", divide="ignore"):
            result = a * np.power(stage, b)

    result = np.where(out_of_range_mask, np.nan, result)  # noqa

    output_df = pd.DataFrame({
        TIMESTAMP_COL: df[TIMESTAMP_COL],
        RESULT_COL: result.astype(np.float64),
    })

    if out_of_range == "drop":
        output_df = output_df[output_df[RESULT_COL].notna()].reset_index(drop=True)

    elif out_of_range == "ndv":
        output_df[RESULT_COL] = output_df[RESULT_COL].fillna(no_data_value)

    logger.info(
        "Rating curve produced %d row(s) from %d input row(s).",
        len(output_df), input_rows,
    )

    return output_df