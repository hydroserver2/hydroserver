import polars as pl
import pytest
from datetime import datetime, timezone

from hydroserverpy.products.expression import validate_expression, apply_expression
from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL, SCHEMA


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _make_df(timestamps, values):
    us = [int(t.timestamp() * 1_000_000) for t in timestamps]
    return pl.DataFrame({
        TIMESTAMP_COL: pl.Series(us, dtype=pl.Int64).cast(pl.Datetime("us", "UTC")),
        RESULT_COL: pl.Series(list(values), dtype=pl.Float64),
    })


def _hourly(count, start_hour=0):
    return [_utc(2024, 1, 1, start_hour + i) for i in range(count)]


# ---------------------------------------------------------------------------
# validate_expression
# ---------------------------------------------------------------------------

class TestValidateExpression:

    def test_simple_arithmetic_passes(self):
        validate_expression("x + 1", ["x"])

    def test_single_variable_passes(self):
        validate_expression("x", ["x"])

    def test_multiple_variables_pass(self):
        validate_expression("x + y", ["x", "y"])

    def test_numeric_constant_passes(self):
        validate_expression("x * 2.5", ["x"])

    def test_allowed_function_passes(self):
        validate_expression("sqrt(x)", ["x"])

    def test_all_allowed_functions_pass(self):
        for fn in ["abs", "min", "max", "sqrt", "log", "log10", "log2", "exp",
                   "sin", "cos", "tan", "asin", "acos", "atan", "floor", "ceil"]:
            validate_expression(f"{fn}(x)", ["x"])

    def test_unary_negation_passes(self):
        validate_expression("-x", ["x"])

    def test_nested_expression_passes(self):
        validate_expression("sqrt(x * x + y * y)", ["x", "y"])

    def test_variable_name_conflicting_with_function_raises(self):
        with pytest.raises(ValueError, match="conflict"):
            validate_expression("sin + 1", ["sin"])

    def test_syntax_error_raises(self):
        with pytest.raises(ValueError, match="syntax"):
            validate_expression("x +* y", ["x", "y"])

    def test_unknown_variable_raises(self):
        with pytest.raises(ValueError, match="unknown"):
            validate_expression("x + z", ["x"])

    def test_unknown_function_call_raises(self):
        with pytest.raises(ValueError, match="unsupported"):
            validate_expression("foo(x)", ["x"])

    def test_boolean_literal_raises(self):
        with pytest.raises(ValueError, match="disallowed"):
            validate_expression("True", [])

    def test_string_literal_raises(self):
        with pytest.raises(ValueError, match="disallowed"):
            validate_expression("'hello'", [])

    def test_disallowed_ast_node_raises(self):
        # ** uses ast.Pow which is not in the whitelist
        with pytest.raises(ValueError, match="disallowed"):
            validate_expression("x ** 2", ["x"])

    def test_conditional_expression_raises(self):
        # if/else uses ast.IfExp, which is not in the whitelist
        with pytest.raises(ValueError, match="disallowed"):
            validate_expression("x if x > 0 else 0", ["x"])

    def test_list_literal_raises(self):
        with pytest.raises(ValueError, match="disallowed"):
            validate_expression("[1, 2]", [])


# ---------------------------------------------------------------------------
# apply_expression
# ---------------------------------------------------------------------------

class TestApplyExpression:

    def test_empty_inputs_raises(self):
        with pytest.raises(ValueError, match="At least one"):
            apply_expression({}, formula="x")

    def test_multiple_inputs_without_interval_raises(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="interval is required"):
            apply_expression({"x": df, "y": df}, formula="x + y")

    def test_on_missing_without_interval_raises(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="interval"):
            apply_expression({"x": df}, formula="x", on_missing="interpolate")

    def test_max_gap_without_interpolate_raises(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="on_missing"):
            apply_expression({"x": df}, formula="x", interval="1h", on_missing="drop", max_gap="2h")

    def test_interpolation_without_interpolate_raises(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="on_missing"):
            apply_expression({"x": df}, formula="x", interval="1h", on_missing="drop", interpolation="nearest")

    def test_single_input_passthrough_preserves_timestamps(self):
        ts = _hourly(3)
        df = _make_df(ts, [1.0, 2.0, 3.0])
        result = apply_expression({"x": df}, formula="x")
        assert result.height == 3

    def test_multiply_by_scalar(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        result = apply_expression({"x": df}, formula="x * 2")
        assert result[RESULT_COL].to_list() == pytest.approx([2.0, 4.0, 6.0])

    def test_add_constant(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        result = apply_expression({"x": df}, formula="x + 10")
        assert result[RESULT_COL].to_list() == pytest.approx([11.0, 12.0, 13.0])

    def test_subtract_constant(self):
        df = _make_df(_hourly(3), [5.0, 10.0, 15.0])
        result = apply_expression({"x": df}, formula="x - 5")
        assert result[RESULT_COL].to_list() == pytest.approx([0.0, 5.0, 10.0])

    def test_divide_by_constant(self):
        df = _make_df(_hourly(3), [2.0, 4.0, 6.0])
        result = apply_expression({"x": df}, formula="x / 2")
        assert result[RESULT_COL].to_list() == pytest.approx([1.0, 2.0, 3.0])

    def test_sqrt_function(self):
        df = _make_df(_hourly(3), [1.0, 4.0, 9.0])
        result = apply_expression({"x": df}, formula="sqrt(x)")
        assert result[RESULT_COL].to_list() == pytest.approx([1.0, 2.0, 3.0])

    def test_abs_function(self):
        df = _make_df(_hourly(3), [-1.0, 0.0, 1.0])
        result = apply_expression({"x": df}, formula="abs(x)")
        assert result[RESULT_COL].to_list() == pytest.approx([1.0, 0.0, 1.0])

    def test_multiple_inputs_addition(self):
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, 2.0, 3.0])
        df_y = _make_df(ts, [4.0, 5.0, 6.0])
        result = apply_expression({"x": df_x, "y": df_y}, formula="x + y", interval="1h")
        assert result[RESULT_COL].to_list() == pytest.approx([5.0, 7.0, 9.0])

    def test_multiple_inputs_formula_with_constants(self):
        ts = _hourly(3)
        df_x = _make_df(ts, [2.0, 4.0, 6.0])
        df_y = _make_df(ts, [1.0, 2.0, 3.0])
        result = apply_expression({"x": df_x, "y": df_y}, formula="x / y", interval="1h")
        assert result[RESULT_COL].to_list() == pytest.approx([2.0, 2.0, 2.0])

    def test_output_result_dtype_is_float64(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        result = apply_expression({"x": df}, formula="x")
        assert result.schema[RESULT_COL] == pl.Float64

    def test_output_timestamp_dtype_matches_canonical_schema(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        result = apply_expression({"x": df}, formula="x")
        assert result.schema[TIMESTAMP_COL] == SCHEMA[TIMESTAMP_COL]

    def test_on_missing_drop_removes_unmatched_grid_points(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [1.0, 3.0])
        result = apply_expression({"x": df}, formula="x", interval="1h", on_missing="drop")
        assert result.height == 2

    def test_on_missing_interpolate_fills_gaps(self):
        ts = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df = _make_df(ts, [0.0, 2.0])
        result = apply_expression({"x": df}, formula="x", interval="1h", on_missing="interpolate")
        assert result.height == 3
        mid_val = result.sort(TIMESTAMP_COL)[RESULT_COL][1]
        assert mid_val == pytest.approx(1.0)

    def test_multi_input_inner_join_drops_unaligned_timestamps(self):
        ts_x = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 1), _utc(2024, 1, 1, 2)]
        ts_y = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df_x = _make_df(ts_x, [1.0, 2.0, 3.0])
        df_y = _make_df(ts_y, [10.0, 30.0])
        result = apply_expression({"x": df_x, "y": df_y}, formula="x + y", interval="1h", on_missing="drop")
        assert result.height == 2
