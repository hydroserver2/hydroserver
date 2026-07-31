import ast
import logging

import numpy as np
import pandas as pd

from pydantic import ConfigDict, validate_call

from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, validate_timeseries


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
    inputs: dict[str, pd.DataFrame],
    formula: str,
    *,
    stop_on_no_data: bool,
    stop_on_error: bool,
    input_no_data_values: dict[str, float] | None = None,
    output_no_data_value: float | None = None,
) -> pd.DataFrame:
    """
    Apply a mathematical formula to one or more input timeseries DataFrames.

    Inputs are matched on exact timestamp (sorted defensively first). If they
    diverge — one has a timestamp the others don't — output stops before that
    point, and it's logged; nothing after is evaluated, even if they realign
    later.

    Within the aligned rows, stop_on_no_data and stop_on_error each
    independently control a bad row (an input at its own no-data value, per
    input_no_data_values, or a non-finite formula result): True truncates
    there and logs it, False fills it with output_no_data_value and
    continues silently.
    """

    if not inputs:
        raise ValueError("At least one input DataFrame must be provided to run an expression.")

    if not stop_on_no_data and output_no_data_value is None:
        raise ValueError("output_no_data_value is required when stop_on_no_data is False.")

    if not stop_on_error and output_no_data_value is None:
        raise ValueError("output_no_data_value is required when stop_on_error is False.")

    variables = list(inputs.keys())
    validate_expression(formula, variables)

    validated = {
        var: validate_timeseries(df).sort_values(TIMESTAMP_COL).reset_index(drop=True)
        for var, df in inputs.items()
    }

    logger.debug(
        "Evaluating expression (formula=%r, variables=%r, stopOnNoData=%r, stopOnError=%r, "
        "inputNoDataValues=%r, outputNoDataValue=%r, rows=%r).",
        formula, variables, stop_on_no_data, stop_on_error, input_no_data_values, output_no_data_value,
        {var: len(df) for var, df in validated.items()},
    )

    timestamp_sets = [set(df[TIMESTAMP_COL]) for df in validated.values()]
    aligned_timestamps = set.intersection(*timestamp_sets)
    divergent_timestamps = set.union(*timestamp_sets) - aligned_timestamps
    divergence_timestamp = min(divergent_timestamps) if divergent_timestamps else None

    combined_df = validated[variables[0]][[TIMESTAMP_COL, RESULT_COL]].rename(columns={RESULT_COL: variables[0]})
    for var in variables[1:]:
        other = validated[var][[TIMESTAMP_COL, RESULT_COL]].rename(columns={RESULT_COL: var})
        combined_df = combined_df.merge(other, on=TIMESTAMP_COL, how="inner")
    combined_df = combined_df.sort_values(TIMESTAMP_COL).reset_index(drop=True)

    if divergence_timestamp is not None:
        combined_df = combined_df[combined_df[TIMESTAMP_COL] < divergence_timestamp].reset_index(drop=True)

    if len(combined_df) == 0:
        if divergence_timestamp is not None:
            logger.warning(
                "Expression stopped at %s: input timestamps are not aligned.", divergence_timestamp,
            )
        return pd.DataFrame({
            TIMESTAMP_COL: pd.Series([], dtype="datetime64[us, UTC]"),
            RESULT_COL: pd.Series([], dtype=np.float64),
        })

    ndv_mask = np.zeros(len(combined_df), dtype=bool)
    if input_no_data_values:
        for var in variables:
            ndv = input_no_data_values.get(var)
            if ndv is not None:
                ndv_mask |= combined_df[var].to_numpy() == ndv

    # __builtins__ is stripped so the formula can't reach outside the math
    # namespace. Evaluated across all rows, including no-data ones; those
    # results get overwritten below.
    compiled_formula = compile(ast.parse(formula.strip(), mode="eval"), "<formula>", "eval")
    namespace = {var: combined_df[var].to_numpy() for var in variables}
    namespace.update(_MATH_NAMESPACE)

    with np.errstate(invalid="ignore", divide="ignore"):
        try:
            result_array = np.asarray(eval(compiled_formula, {"__builtins__": {}}, namespace), dtype=np.float64)
        except Exception as e:
            raise ValueError(f"Formula evaluation failed: {e}") from e

    # Excludes no-data rows, which stop_on_no_data already accounts for.
    error_mask = ~ndv_mask & ~np.isfinite(result_array)

    ndv_stop_idx = int(np.argmax(ndv_mask)) if stop_on_no_data and ndv_mask.any() else None
    error_stop_idx = int(np.argmax(error_mask)) if stop_on_error and error_mask.any() else None

    stop_idx = None
    stop_reason = None
    if ndv_stop_idx is not None and (error_stop_idx is None or ndv_stop_idx <= error_stop_idx):
        stop_idx, stop_reason = ndv_stop_idx, "input(s) contained a no-data value"
    elif error_stop_idx is not None:
        stop_idx, stop_reason = error_stop_idx, "formula produced a non-finite result"

    if stop_idx is not None:
        stop_timestamp = combined_df[TIMESTAMP_COL].iloc[stop_idx]
        combined_df = combined_df.iloc[:stop_idx].reset_index(drop=True)
        result_array = result_array[:stop_idx]
        ndv_mask = ndv_mask[:stop_idx]
        error_mask = error_mask[:stop_idx]
        logger.warning("Expression stopped at %s: %s.", stop_timestamp, stop_reason)
    elif divergence_timestamp is not None:
        logger.warning(
            "Expression stopped at %s: input timestamps are not aligned.", divergence_timestamp,
        )

    if not stop_on_no_data and ndv_mask.any():
        result_array = np.where(ndv_mask, output_no_data_value, result_array)

    if not stop_on_error and error_mask.any():
        result_array = np.where(error_mask, output_no_data_value, result_array)

    result = pd.DataFrame({
        TIMESTAMP_COL: combined_df[TIMESTAMP_COL],
        RESULT_COL: result_array,
    })

    logger.info(
        "Expression produced %d row(s) from %d input variable(s).",
        len(result), len(inputs),
    )

    return result
