import logging

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone

from hydroserverpy.products.expression import validate_expression, apply_expression
from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _make_df(timestamps, values):
    return pd.DataFrame({
        TIMESTAMP_COL: pd.DatetimeIndex(timestamps).as_unit("us"),
        RESULT_COL: np.array(list(values), dtype=np.float64),
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
            apply_expression({}, formula="x", stop_on_no_data=True, stop_on_error=True)

    def test_stop_on_no_data_false_requires_output_no_data_value(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="output_no_data_value"):
            apply_expression({"x": df}, formula="x", stop_on_no_data=False, stop_on_error=True)

    def test_stop_on_error_false_requires_output_no_data_value(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="output_no_data_value"):
            apply_expression({"x": df}, formula="x", stop_on_no_data=True, stop_on_error=False)

    def test_single_input_passthrough_preserves_timestamps(self):
        ts = _hourly(3)
        df = _make_df(ts, [1.0, 2.0, 3.0])
        result = apply_expression({"x": df}, formula="x", stop_on_no_data=True, stop_on_error=True)
        assert len(result) == 3
        assert result[TIMESTAMP_COL].tolist() == df[TIMESTAMP_COL].tolist()

    def test_single_input_sorted_defensively(self):
        ts = list(reversed(_hourly(3)))
        df = _make_df(ts, [3.0, 2.0, 1.0])
        result = apply_expression({"x": df}, formula="x", stop_on_no_data=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([1.0, 2.0, 3.0])
        assert result[TIMESTAMP_COL].is_monotonic_increasing

    def test_multiply_by_scalar(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        result = apply_expression({"x": df}, formula="x * 2", stop_on_no_data=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([2.0, 4.0, 6.0])

    def test_add_constant(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        result = apply_expression({"x": df}, formula="x + 10", stop_on_no_data=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([11.0, 12.0, 13.0])

    def test_subtract_constant(self):
        df = _make_df(_hourly(3), [5.0, 10.0, 15.0])
        result = apply_expression({"x": df}, formula="x - 5", stop_on_no_data=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([0.0, 5.0, 10.0])

    def test_divide_by_constant(self):
        df = _make_df(_hourly(3), [2.0, 4.0, 6.0])
        result = apply_expression({"x": df}, formula="x / 2", stop_on_no_data=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([1.0, 2.0, 3.0])

    def test_sqrt_function(self):
        df = _make_df(_hourly(3), [1.0, 4.0, 9.0])
        result = apply_expression({"x": df}, formula="sqrt(x)", stop_on_no_data=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([1.0, 2.0, 3.0])

    def test_abs_function(self):
        df = _make_df(_hourly(3), [-1.0, 0.0, 1.0])
        result = apply_expression({"x": df}, formula="abs(x)", stop_on_no_data=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([1.0, 0.0, 1.0])

    def test_output_result_dtype_is_float64(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        result = apply_expression({"x": df}, formula="x", stop_on_no_data=True, stop_on_error=True)
        assert pd.api.types.is_float_dtype(result[RESULT_COL])

    def test_output_timestamp_dtype_matches_canonical_schema(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        result = apply_expression({"x": df}, formula="x", stop_on_no_data=True, stop_on_error=True)
        assert pd.api.types.is_datetime64_any_dtype(result[TIMESTAMP_COL])

    # -- Multi-input alignment --------------------------------------------

    def test_multiple_inputs_addition_on_matching_timestamps(self):
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, 2.0, 3.0])
        df_y = _make_df(ts, [4.0, 5.0, 6.0])
        result = apply_expression(
            {"x": df_x, "y": df_y}, formula="x + y", stop_on_no_data=True, stop_on_error=True
        )
        assert result[RESULT_COL].tolist() == pytest.approx([5.0, 7.0, 9.0])

    def test_multiple_inputs_formula_with_division(self):
        ts = _hourly(3)
        df_x = _make_df(ts, [2.0, 4.0, 6.0])
        df_y = _make_df(ts, [1.0, 2.0, 3.0])
        result = apply_expression(
            {"x": df_x, "y": df_y}, formula="x / y", stop_on_no_data=True, stop_on_error=True
        )
        assert result[RESULT_COL].tolist() == pytest.approx([2.0, 2.0, 2.0])

    def test_inputs_sorted_defensively_before_joining(self):
        ts = _hourly(3)
        df_x = _make_df(list(reversed(ts)), [3.0, 2.0, 1.0])
        df_y = _make_df(ts, [10.0, 20.0, 30.0])
        result = apply_expression(
            {"x": df_x, "y": df_y}, formula="x + y", stop_on_no_data=True, stop_on_error=True
        )
        assert result[RESULT_COL].tolist() == pytest.approx([11.0, 22.0, 33.0])

    def test_misalignment_stops_before_first_divergent_timestamp(self, caplog):
        # x has an extra reading at hour 1 that y never reports.
        ts_x = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 1), _utc(2024, 1, 1, 2)]
        ts_y = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df_x = _make_df(ts_x, [1.0, 2.0, 3.0])
        df_y = _make_df(ts_y, [10.0, 30.0])
        with caplog.at_level(logging.WARNING):
            result = apply_expression(
                {"x": df_x, "y": df_y}, formula="x + y", stop_on_no_data=True, stop_on_error=True
            )
        # Hour 2 matched on both sides, but comes after the hour-1 divergence,
        # so it's excluded even though it would otherwise be a valid match.
        assert result[TIMESTAMP_COL].tolist() == [_utc(2024, 1, 1, 0)]
        assert result[RESULT_COL].tolist() == pytest.approx([11.0])
        assert "not aligned" in caplog.text

    def test_fully_aligned_inputs_produce_no_warning(self, caplog):
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, 2.0, 3.0])
        df_y = _make_df(ts, [4.0, 5.0, 6.0])
        with caplog.at_level(logging.WARNING):
            apply_expression(
                {"x": df_x, "y": df_y}, formula="x + y", stop_on_no_data=True, stop_on_error=True
            )
        assert caplog.text == ""

    def test_completely_disjoint_timestamps_return_empty(self):
        df_x = _make_df([_utc(2024, 1, 1, 0)], [1.0])
        df_y = _make_df([_utc(2024, 1, 1, 1)], [2.0])
        result = apply_expression(
            {"x": df_x, "y": df_y}, formula="x + y", stop_on_no_data=True, stop_on_error=True
        )
        assert len(result) == 0

    # -- stop_on_no_data (no-data values in aligned inputs) -----------------

    def test_stop_on_no_data_false_fills_and_continues(self):
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, -9999.0, 3.0])
        df_y = _make_df(ts, [10.0, 20.0, 30.0])
        result = apply_expression(
            {"x": df_x, "y": df_y}, formula="x + y",
            stop_on_no_data=False, stop_on_error=True,
            input_no_data_values={"x": -9999.0, "y": -9999.0}, output_no_data_value=-9999.0,
        )
        assert len(result) == 3
        assert result[RESULT_COL].tolist() == pytest.approx([11.0, -9999.0, 33.0])

    def test_stop_on_no_data_true_truncates_at_first_no_data_value(self, caplog):
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, -9999.0, 3.0])
        df_y = _make_df(ts, [10.0, 20.0, 30.0])
        with caplog.at_level(logging.WARNING):
            result = apply_expression(
                {"x": df_x, "y": df_y}, formula="x + y",
                stop_on_no_data=True, stop_on_error=True,
                input_no_data_values={"x": -9999.0, "y": -9999.0},
            )
        assert result[RESULT_COL].tolist() == pytest.approx([11.0])
        assert "no-data value" in caplog.text

    def test_stop_on_no_data_only_checks_that_inputs_own_sentinel(self):
        # x's sentinel (-9999) never appears in y, and y's sentinel (-777)
        # never appears in x, so neither input's real values are misdetected
        # as no-data, and both real no-data rows are still caught.
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, -9999.0, 3.0])
        df_y = _make_df(ts, [10.0, 20.0, -777.0])
        result = apply_expression(
            {"x": df_x, "y": df_y}, formula="x + y",
            stop_on_no_data=False, stop_on_error=True,
            input_no_data_values={"x": -9999.0, "y": -777.0}, output_no_data_value=-1.0,
        )
        assert result[RESULT_COL].tolist() == pytest.approx([11.0, -1.0, -1.0])

    # -- stop_on_error (non-finite formula results) --------------------------

    def test_stop_on_error_false_fills_and_continues(self):
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, 2.0, 3.0])
        df_y = _make_df(ts, [1.0, 0.0, 3.0])
        result = apply_expression(
            {"x": df_x, "y": df_y}, formula="x / y",
            stop_on_no_data=True, stop_on_error=False, output_no_data_value=-9999.0,
        )
        assert len(result) == 3
        assert result[RESULT_COL].tolist() == pytest.approx([1.0, -9999.0, 1.0])

    def test_stop_on_error_true_truncates_at_first_non_finite_result(self, caplog):
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, 2.0, 3.0])
        df_y = _make_df(ts, [1.0, 0.0, 3.0])
        with caplog.at_level(logging.WARNING):
            result = apply_expression(
                {"x": df_x, "y": df_y}, formula="x / y", stop_on_no_data=True, stop_on_error=True
            )
        assert result[RESULT_COL].tolist() == pytest.approx([1.0])
        assert "non-finite" in caplog.text

    def test_no_data_value_rows_are_not_also_flagged_as_errors(self):
        # A no-data sentinel fed into the formula could itself produce a
        # non-finite result (e.g. via log); stop_on_no_data must claim that
        # row, not stop_on_error, even when stop_on_error is True.
        ts = _hourly(2)
        df_x = _make_df(ts, [-9999.0, 4.0])
        result = apply_expression(
            {"x": df_x}, formula="log(x)",
            stop_on_no_data=False, stop_on_error=True,
            input_no_data_values={"x": -9999.0}, output_no_data_value=-9999.0,
        )
        assert len(result) == 2
        assert result[RESULT_COL].tolist() == pytest.approx([-9999.0, np.log(4.0)])
