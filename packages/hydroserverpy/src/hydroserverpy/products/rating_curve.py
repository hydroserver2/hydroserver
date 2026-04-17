import logging

import numpy as np
import polars as pl

from typing import Literal
from pydantic import ConfigDict, validate_call

from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, validate_timeseries


logger = logging.getLogger(__name__)


@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def apply_rating_curve(
    df: pl.DataFrame,
    *,
    breakpoints: list[tuple[float, float]],
    method: Literal["linear", "power_law"] = "linear",
    out_of_range: Literal["drop", "raise", "stop"] = "drop",
    no_data_value: float | None = None,
) -> pl.DataFrame:
    """
    Apply a rating curve to a stage timeseries to produce a discharge timeseries.

    Breakpoints define the curve as (stage, discharge) pairs. For 'linear', discharge
    is interpolated piecewise between adjacent breakpoints. For 'power_law', a curve
    of the form y = a·xᵇ is fitted to all breakpoints via log-log regression.

    The out_of_range input controls behavior when a stage value falls outside the breakpoint
    range (or is non-positive for power_law): 'drop' omits those rows, 'raise' raises
    a ValueError, and 'stop' returns rows up to the first out-of-range value.
    """

    validate_timeseries(df)

    input_rows = df.height
    logger.debug(
        "Applying rating curve to %d row(s) (method=%r, breakpoints=%d, outOfRange=%r, noDataValue=%r).",
        input_rows, method, len(breakpoints), out_of_range, no_data_value,
    )

    if no_data_value is not None:
        df = df.filter(pl.col(RESULT_COL) != no_data_value)
        dropped = input_rows - df.height
        if dropped:
            logger.debug("Dropped %d no-data row(s) (noDataValue=%r).", dropped, no_data_value)

    if len(breakpoints) < 2:
        raise ValueError("At least 2 breakpoints are required.")

    sorted_breakpoints = sorted(breakpoints, key=lambda p: p[0])
    xs = np.array([point[0] for point in sorted_breakpoints], dtype=np.float64)
    ys = np.array([point[1] for point in sorted_breakpoints], dtype=np.float64)

    if method == "power_law":
        if (xs <= 0).any() or (ys <= 0).any():
            raise ValueError("power_law requires all breakpoint values to be positive.")

    stage = df[RESULT_COL].to_numpy(allow_copy=True)

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
        df = df.slice(0, first_out_of_range)
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

    output_df = pl.DataFrame(
        {
            TIMESTAMP_COL: df[TIMESTAMP_COL],
            RESULT_COL: result,
        }
    ).with_columns(pl.col(RESULT_COL).cast(pl.Float64))

    if out_of_range == "drop":
        output_df = output_df.filter(pl.col(RESULT_COL).is_not_nan())

    logger.info(
        "Rating curve produced %d row(s) from %d input row(s).",
        output_df.height, input_rows,
    )

    return output_df
