import ast
import logging

import polars as pl
import numpy as np

from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, validate_call

from hydroserverpy.core.duration import Duration
from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, align_timeseries


logger = logging.getLogger(__name__)


_ALLOWED_NODE_TYPES = frozenset({
    ast.Expression,
    ast.BinOp,
    ast.Add, ast.Sub, ast.Mult, ast.Div,
    ast.UnaryOp, ast.UAdd, ast.USub,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Call,
})

_ALLOWED_FUNCTIONS = frozenset({
    "abs", "min", "max",
    "sqrt", "log", "log10", "log2", "exp",
    "sin", "cos", "tan", "asin", "acos", "atan",
    "floor", "ceil",
})

_MATH_NAMESPACE: dict = {
    "abs": np.abs,
    "min": np.minimum,
    "max": np.maximum,
    "sqrt": np.sqrt,
    "log": np.log,
    "log10": np.log10,
    "log2": np.log2,
    "exp": np.exp,
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "asin": np.arcsin,
    "acos": np.arccos,
    "atan": np.arctan,
    "floor": np.floor,
    "ceil": np.ceil,
}


def validate_expression(formula: str, variables: list[str]) -> None:
    """
    Validate a formula string against the approved AST whitelist and variable names.

    Raises ValueError if:
      - Any variable name conflicts with an approved function name.
      - The formula fails to parse as a Python expression.
      - The formula contains any disallowed AST node type.
      - The formula contains a non-numeric or boolean literal.
      - The formula references a name not in variables or approved functions.
      - The formula calls a function not in the approved functions list.
    """

    if conflicts := set(variables) & _ALLOWED_FUNCTIONS:
        raise ValueError(
            f"Variable names conflict with expression functions: {sorted(conflicts)}."
        )

    try:
        tree = ast.parse(formula.strip(), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Formula syntax error: {e}") from e

    allowed_names = set(variables) | _ALLOWED_FUNCTIONS

    for node in ast.walk(tree):
        if type(node) not in _ALLOWED_NODE_TYPES:
            raise ValueError(
                f"Formula contains a disallowed construct: {type(node).__name__!r}."
            )
        if isinstance(node, ast.Constant) and (
            isinstance(node.value, bool) or not isinstance(node.value, (int, float))
        ):
            raise ValueError(
                f"Formula contains a disallowed literal {node.value!r}. "
                "Only numeric literals are permitted."
            )
        if isinstance(node, ast.Name) and node.id not in allowed_names:
            raise ValueError(
                f"Formula references unknown name '{node.id}'. "
                f"Known variables: {sorted(variables)}. "
                f"Approved functions: {sorted(_ALLOWED_FUNCTIONS)}."
            )
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCTIONS:
                raise ValueError(
                    f"Formula calls unsupported function '{ast.unparse(node.func)}'. "
                    f"Approved functions: {sorted(_ALLOWED_FUNCTIONS)}."
                )


@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def apply_expression(
    inputs: dict[str, pl.DataFrame],
    formula: str,
    *,
    interval: Duration | None = None,
    anchor: datetime | None = None,
    on_missing: Literal["drop", "interpolate", "raise", "stop"] = "drop",
    interpolation: Literal["linear", "nearest"] = "linear",
    max_gap: Duration | None = None,
    no_data_value: float | None = None,
) -> pl.DataFrame:
    """
    Apply a mathematical formula to one or more input timeseries DataFrames.

    For a single input, timestamps carry across unchanged unless an interval is set,
    in which case the time series is snapped to a regular grid before evaluation.
    For multiple inputs, an interval is required — each input is independently aligned
    to the grid, then inner-joined on timestamp before the formula is evaluated.
    """

    if not inputs:
        raise ValueError("At least one input DataFrame must be provided to run an expression.")

    if len(inputs) > 1 and interval is None:
        raise ValueError("interval is required when multiple inputs are provided.")

    if interval is None and on_missing != "drop":
        raise ValueError("on_missing requires interval to be set.")

    if interval is None and interpolation != "linear":
        raise ValueError("interpolation requires interval to be set.")

    if interval is None and max_gap is not None:
        raise ValueError("max_gap requires interval to be set.")

    if max_gap is not None and on_missing != "interpolate":
        raise ValueError("max_gap requires on_missing='interpolate'.")

    if interpolation != "linear" and on_missing != "interpolate":
        raise ValueError("interpolation requires on_missing='interpolate'.")

    validate_expression(formula, list(inputs.keys()))

    input_rows = {k: v.height for k, v in inputs.items()}
    logger.debug(
        "Evaluating expression (formula=%r, variables=%r, interval=%r, noDataValue=%r, rows=%r).",
        formula, list(inputs.keys()), interval, no_data_value, input_rows,
    )

    if no_data_value is not None:
        inputs = {k: v.filter(pl.col(RESULT_COL) != no_data_value) for k, v in inputs.items()}
        for k, before in input_rows.items():
            dropped = before - inputs[k].height
            if dropped:
                logger.debug("Dropped %d no-data row(s) from %r (noDataValue=%r).", dropped, k, no_data_value)

    # When an interval is set, snap each input independently to the regular grid.
    # on_missing, interpolation, and max_gap are handled per-input at this stage.
    # Without interval, a single input passes through with its original timestamps.
    if interval is not None:
        aligned = {
            var: align_timeseries(
                df,
                interval=interval,
                anchor=anchor,
                on_missing=on_missing,
                interpolation=interpolation,
                max_gap=max_gap,
            )
            for var, df in inputs.items()
        }
    else:
        aligned = inputs

    # Inner join all inputs on timestamp. For multiple aligned inputs this
    # drops any timestamp where any input has no value (e.g., dropped by
    # on_missing="drop" during alignment), ensuring the formula always
    # receives a complete set of values at every output timestamp.
    variables = list(inputs.keys())
    combined = (
        aligned[variables[0]]
        .select([TIMESTAMP_COL, RESULT_COL])
        .rename({RESULT_COL: variables[0]})
    )
    for var in variables[1:]:
        other = aligned[var].select([TIMESTAMP_COL, RESULT_COL]).rename({RESULT_COL: var})
        combined = combined.join(other, on=TIMESTAMP_COL, how="inner")
    combined = combined.sort(TIMESTAMP_COL)

    # Compile the formula once, then evaluate it against numpy arrays extracted
    # from each variable column. __builtins__ is stripped to prevent any access
    # to Python builtins outside the approved math namespace.
    compiled = compile(ast.parse(formula.strip(), mode="eval"), "<formula>", "eval")
    namespace = {
        var: combined[var].to_numpy(allow_copy=True)
        for var in inputs
    }
    namespace.update(_MATH_NAMESPACE)

    try:
        result_array = eval(compiled, {"__builtins__": {}}, namespace)
    except Exception as e:
        raise ValueError(f"Formula evaluation failed: {e}") from e

    result = pl.DataFrame(
        {
            TIMESTAMP_COL: combined[TIMESTAMP_COL],
            RESULT_COL: result_array,
        }
    ).with_columns(pl.col(RESULT_COL).cast(pl.Float64))

    logger.info(
        "Expression produced %d row(s) from %d input variable(s).",
        result.height, len(inputs),
    )

    return result
