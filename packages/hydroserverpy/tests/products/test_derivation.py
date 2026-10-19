import logging

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone

from hydroserverpy.products.derivation import validate_derivation_formula, apply_derivation
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
# validate_derivation_formula
# ---------------------------------------------------------------------------

class TestValidateDerivationFormula:

    def test_simple_arithmetic_passes(self):
        validate_derivation_formula("x + 1", ["x"])

    def test_single_variable_passes(self):
        validate_derivation_formula("x", ["x"])

    def test_multiple_variables_pass(self):
        validate_derivation_formula("x + y", ["x", "y"])

    def test_numeric_constant_passes(self):
        validate_derivation_formula("x * 2.5", ["x"])

    def test_allowed_function_passes(self):
        validate_derivation_formula("sqrt(x)", ["x"])

    def test_all_allowed_functions_pass(self):
        for fn in ["abs", "min", "max", "sqrt", "log", "log10", "log2", "exp",
                   "sin", "cos", "tan", "asin", "acos", "atan", "floor", "ceil"]:
            validate_derivation_formula(f"{fn}(x)", ["x"])

    def test_unary_negation_passes(self):
        validate_derivation_formula("-x", ["x"])

    def test_nested_expression_passes(self):
        validate_derivation_formula("sqrt(x * x + y * y)", ["x", "y"])

    def test_variable_name_conflicting_with_function_raises(self):
        with pytest.raises(ValueError, match="conflict"):
            validate_derivation_formula("sin + 1", ["sin"])

    def test_syntax_error_raises(self):
        with pytest.raises(ValueError, match="syntax"):
            validate_derivation_formula("x +* y", ["x", "y"])

    def test_unknown_variable_raises(self):
        with pytest.raises(ValueError, match="unknown"):
            validate_derivation_formula("x + z", ["x"])

    def test_unknown_function_call_raises(self):
        with pytest.raises(ValueError, match="unsupported"):
            validate_derivation_formula("foo(x)", ["x"])

    def test_boolean_literal_raises(self):
        with pytest.raises(ValueError, match="disallowed"):
            validate_derivation_formula("True", [])

    def test_string_literal_raises(self):
        with pytest.raises(ValueError, match="disallowed"):
            validate_derivation_formula("'hello'", [])

    def test_disallowed_ast_node_raises(self):
        # ** uses ast.Pow which is not in the whitelist
        with pytest.raises(ValueError, match="disallowed"):
            validate_derivation_formula("x ** 2", ["x"])

    def test_conditional_expression_raises(self):
        # if/else uses ast.IfExp, which is not in the whitelist
        with pytest.raises(ValueError, match="disallowed"):
            validate_derivation_formula("x if x > 0 else 0", ["x"])

    def test_list_literal_raises(self):
        with pytest.raises(ValueError, match="disallowed"):
            validate_derivation_formula("[1, 2]", [])


# ---------------------------------------------------------------------------
# apply_derivation
# ---------------------------------------------------------------------------

class TestApplyDerivation:

    def test_empty_inputs_raises(self):
        with pytest.raises(ValueError, match="At least one"):
            apply_derivation({}, formula="x", stop_on_gaps=True, stop_on_error=True)

    def test_input_no_data_values_require_output_no_data_value(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="output_no_data_value"):
            apply_derivation(
                {"x": df}, formula="x", stop_on_gaps=True, stop_on_error=True,
                input_no_data_values={"x": -9999.0},
            )

    def test_stop_on_gaps_false_does_not_require_output_no_data_value(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        result = apply_derivation({"x": df}, formula="x", stop_on_gaps=False, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([1.0, 2.0, 3.0])

    def test_stop_on_error_false_requires_output_no_data_value(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="output_no_data_value"):
            apply_derivation({"x": df}, formula="x", stop_on_gaps=True, stop_on_error=False)

    def test_single_input_passthrough_preserves_timestamps(self):
        ts = _hourly(3)
        df = _make_df(ts, [1.0, 2.0, 3.0])
        result = apply_derivation({"x": df}, formula="x", stop_on_gaps=True, stop_on_error=True)
        assert len(result) == 3
        assert result[TIMESTAMP_COL].tolist() == df[TIMESTAMP_COL].tolist()

    def test_single_input_sorted_defensively(self):
        ts = list(reversed(_hourly(3)))
        df = _make_df(ts, [3.0, 2.0, 1.0])
        result = apply_derivation({"x": df}, formula="x", stop_on_gaps=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([1.0, 2.0, 3.0])
        assert result[TIMESTAMP_COL].is_monotonic_increasing

    def test_multiply_by_scalar(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        result = apply_derivation({"x": df}, formula="x * 2", stop_on_gaps=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([2.0, 4.0, 6.0])

    def test_add_constant(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        result = apply_derivation({"x": df}, formula="x + 10", stop_on_gaps=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([11.0, 12.0, 13.0])

    def test_subtract_constant(self):
        df = _make_df(_hourly(3), [5.0, 10.0, 15.0])
        result = apply_derivation({"x": df}, formula="x - 5", stop_on_gaps=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([0.0, 5.0, 10.0])

    def test_divide_by_constant(self):
        df = _make_df(_hourly(3), [2.0, 4.0, 6.0])
        result = apply_derivation({"x": df}, formula="x / 2", stop_on_gaps=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([1.0, 2.0, 3.0])

    def test_sqrt_function(self):
        df = _make_df(_hourly(3), [1.0, 4.0, 9.0])
        result = apply_derivation({"x": df}, formula="sqrt(x)", stop_on_gaps=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([1.0, 2.0, 3.0])

    def test_abs_function(self):
        df = _make_df(_hourly(3), [-1.0, 0.0, 1.0])
        result = apply_derivation({"x": df}, formula="abs(x)", stop_on_gaps=True, stop_on_error=True)
        assert result[RESULT_COL].tolist() == pytest.approx([1.0, 0.0, 1.0])

    def test_output_result_dtype_is_float64(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        result = apply_derivation({"x": df}, formula="x", stop_on_gaps=True, stop_on_error=True)
        assert pd.api.types.is_float_dtype(result[RESULT_COL])

    def test_output_timestamp_dtype_matches_canonical_schema(self):
        df = _make_df(_hourly(3), [1.0, 2.0, 3.0])
        result = apply_derivation({"x": df}, formula="x", stop_on_gaps=True, stop_on_error=True)
        assert pd.api.types.is_datetime64_any_dtype(result[TIMESTAMP_COL])

    # -- Multi-input alignment --------------------------------------------

    def test_multiple_inputs_addition_on_matching_timestamps(self):
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, 2.0, 3.0])
        df_y = _make_df(ts, [4.0, 5.0, 6.0])
        result = apply_derivation(
            {"x": df_x, "y": df_y}, formula="x + y", stop_on_gaps=True, stop_on_error=True
        )
        assert result[RESULT_COL].tolist() == pytest.approx([5.0, 7.0, 9.0])

    def test_multiple_inputs_formula_with_division(self):
        ts = _hourly(3)
        df_x = _make_df(ts, [2.0, 4.0, 6.0])
        df_y = _make_df(ts, [1.0, 2.0, 3.0])
        result = apply_derivation(
            {"x": df_x, "y": df_y}, formula="x / y", stop_on_gaps=True, stop_on_error=True
        )
        assert result[RESULT_COL].tolist() == pytest.approx([2.0, 2.0, 2.0])

    def test_inputs_sorted_defensively_before_joining(self):
        ts = _hourly(3)
        df_x = _make_df(list(reversed(ts)), [3.0, 2.0, 1.0])
        df_y = _make_df(ts, [10.0, 20.0, 30.0])
        result = apply_derivation(
            {"x": df_x, "y": df_y}, formula="x + y", stop_on_gaps=True, stop_on_error=True
        )
        assert result[RESULT_COL].tolist() == pytest.approx([11.0, 22.0, 33.0])

    def test_misalignment_stops_before_first_divergent_timestamp(self, caplog):
        # x has an extra reading at hour 1 that y never reports.
        ts_x = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 1), _utc(2024, 1, 1, 2)]
        ts_y = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df_x = _make_df(ts_x, [1.0, 2.0, 3.0])
        df_y = _make_df(ts_y, [10.0, 30.0])
        with caplog.at_level(logging.WARNING):
            result = apply_derivation(
                {"x": df_x, "y": df_y}, formula="x + y", stop_on_gaps=True, stop_on_error=True
            )
        # Hour 2 matched on both sides, but comes after the hour-1 divergence,
        # so it's excluded even though it would otherwise be a valid match.
        assert result[TIMESTAMP_COL].tolist() == [_utc(2024, 1, 1, 0)]
        assert result[RESULT_COL].tolist() == pytest.approx([11.0])
        assert "not aligned" in caplog.text

    def test_misalignment_skipped_when_stop_on_gaps_false(self, caplog):
        # Same inputs as above, but hour 1 is skipped and hour 2 still matches.
        ts_x = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 1), _utc(2024, 1, 1, 2)]
        ts_y = [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        df_x = _make_df(ts_x, [1.0, 2.0, 3.0])
        df_y = _make_df(ts_y, [10.0, 30.0])
        with caplog.at_level(logging.INFO):
            result = apply_derivation(
                {"x": df_x, "y": df_y}, formula="x + y", stop_on_gaps=False, stop_on_error=True
            )
        assert result[TIMESTAMP_COL].tolist() == [_utc(2024, 1, 1, 0), _utc(2024, 1, 1, 2)]
        assert result[RESULT_COL].tolist() == pytest.approx([11.0, 33.0])
        assert "skipped 1 timestamp" in caplog.text
        assert "stopped" not in caplog.text

    def test_misalignment_skipped_in_both_directions(self):
        # x is missing hour 1 and y is missing hour 3; both are skipped.
        ts_x = [_utc(2024, 1, 1, h) for h in (0, 2, 3, 4)]
        ts_y = [_utc(2024, 1, 1, h) for h in (0, 1, 2, 4)]
        df_x = _make_df(ts_x, [1.0, 3.0, 4.0, 5.0])
        df_y = _make_df(ts_y, [10.0, 20.0, 30.0, 50.0])
        result = apply_derivation(
            {"x": df_x, "y": df_y}, formula="x + y", stop_on_gaps=False, stop_on_error=True
        )
        assert result[TIMESTAMP_COL].tolist() == [_utc(2024, 1, 1, h) for h in (0, 2, 4)]
        assert result[RESULT_COL].tolist() == pytest.approx([11.0, 33.0, 55.0])

    def test_skipped_gap_and_no_data_value_handled_independently(self):
        # Hour 1 is a gap (skipped); hour 2 has x at its no-data value (filled).
        ts_x = [_utc(2024, 1, 1, h) for h in (0, 1, 2, 3)]
        ts_y = [_utc(2024, 1, 1, h) for h in (0, 2, 3)]
        df_x = _make_df(ts_x, [1.0, 2.0, -9999.0, 4.0])
        df_y = _make_df(ts_y, [10.0, 30.0, 40.0])
        result = apply_derivation(
            {"x": df_x, "y": df_y}, formula="x + y",
            stop_on_gaps=False, stop_on_error=True,
            input_no_data_values={"x": -9999.0, "y": -9999.0}, output_no_data_value=-1.0,
        )
        assert result[TIMESTAMP_COL].tolist() == [_utc(2024, 1, 1, h) for h in (0, 2, 3)]
        assert result[RESULT_COL].tolist() == pytest.approx([11.0, -1.0, 44.0])

    def test_stop_on_error_still_applies_after_skipped_gap(self, caplog):
        ts_x = [_utc(2024, 1, 1, h) for h in (0, 1, 2, 3)]
        ts_y = [_utc(2024, 1, 1, h) for h in (0, 2, 3)]
        df_x = _make_df(ts_x, [1.0, 2.0, 3.0, 4.0])
        df_y = _make_df(ts_y, [1.0, 0.0, 4.0])
        with caplog.at_level(logging.WARNING):
            result = apply_derivation(
                {"x": df_x, "y": df_y}, formula="x / y", stop_on_gaps=False, stop_on_error=True
            )
        assert result[TIMESTAMP_COL].tolist() == [_utc(2024, 1, 1, 0)]
        assert "non-finite" in caplog.text

    def test_completely_disjoint_timestamps_return_empty_when_skipping(self, caplog):
        df_x = _make_df([_utc(2024, 1, 1, 0)], [1.0])
        df_y = _make_df([_utc(2024, 1, 1, 1)], [2.0])
        with caplog.at_level(logging.WARNING):
            result = apply_derivation(
                {"x": df_x, "y": df_y}, formula="x + y", stop_on_gaps=False, stop_on_error=True
            )
        assert len(result) == 0
        assert caplog.text == ""

    def test_fully_aligned_inputs_produce_no_warning(self, caplog):
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, 2.0, 3.0])
        df_y = _make_df(ts, [4.0, 5.0, 6.0])
        with caplog.at_level(logging.WARNING):
            apply_derivation(
                {"x": df_x, "y": df_y}, formula="x + y", stop_on_gaps=True, stop_on_error=True
            )
        assert caplog.text == ""

    def test_completely_disjoint_timestamps_return_empty(self):
        df_x = _make_df([_utc(2024, 1, 1, 0)], [1.0])
        df_y = _make_df([_utc(2024, 1, 1, 1)], [2.0])
        result = apply_derivation(
            {"x": df_x, "y": df_y}, formula="x + y", stop_on_gaps=True, stop_on_error=True
        )
        assert len(result) == 0

    # -- No-data values in aligned inputs -----------------------------------

    @pytest.mark.parametrize("stop_on_gaps", [True, False])
    def test_no_data_value_always_fills_and_continues(self, stop_on_gaps, caplog):
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, -9999.0, 3.0])
        df_y = _make_df(ts, [10.0, 20.0, 30.0])
        with caplog.at_level(logging.WARNING):
            result = apply_derivation(
                {"x": df_x, "y": df_y}, formula="x + y",
                stop_on_gaps=stop_on_gaps, stop_on_error=True,
                input_no_data_values={"x": -9999.0, "y": -9999.0}, output_no_data_value=-9999.0,
            )
        assert len(result) == 3
        assert result[RESULT_COL].tolist() == pytest.approx([11.0, -9999.0, 33.0])
        assert caplog.text == ""

    def test_no_data_value_only_checks_that_inputs_own_sentinel(self):
        # x's sentinel (-9999) never appears in y, and y's sentinel (-777)
        # never appears in x, so neither input's real values are misdetected
        # as no-data, and both real no-data rows are still caught.
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, -9999.0, 3.0])
        df_y = _make_df(ts, [10.0, 20.0, -777.0])
        result = apply_derivation(
            {"x": df_x, "y": df_y}, formula="x + y",
            stop_on_gaps=False, stop_on_error=True,
            input_no_data_values={"x": -9999.0, "y": -777.0}, output_no_data_value=-1.0,
        )
        assert result[RESULT_COL].tolist() == pytest.approx([11.0, -1.0, -1.0])

    # -- stop_on_error (non-finite formula results) --------------------------

    def test_stop_on_error_false_fills_and_continues(self):
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, 2.0, 3.0])
        df_y = _make_df(ts, [1.0, 0.0, 3.0])
        result = apply_derivation(
            {"x": df_x, "y": df_y}, formula="x / y",
            stop_on_gaps=True, stop_on_error=False, output_no_data_value=-9999.0,
        )
        assert len(result) == 3
        assert result[RESULT_COL].tolist() == pytest.approx([1.0, -9999.0, 1.0])

    def test_stop_on_error_true_truncates_at_first_non_finite_result(self, caplog):
        ts = _hourly(3)
        df_x = _make_df(ts, [1.0, 2.0, 3.0])
        df_y = _make_df(ts, [1.0, 0.0, 3.0])
        with caplog.at_level(logging.WARNING):
            result = apply_derivation(
                {"x": df_x, "y": df_y}, formula="x / y", stop_on_gaps=True, stop_on_error=True
            )
        assert result[RESULT_COL].tolist() == pytest.approx([1.0])
        assert "non-finite" in caplog.text

    def test_no_data_value_rows_are_not_also_flagged_as_errors(self):
        # A no-data sentinel fed into the formula could itself produce a
        # non-finite result (e.g. via log); it must be filled as no-data, not
        # flagged by stop_on_error, even when stop_on_error is True.
        ts = _hourly(2)
        df_x = _make_df(ts, [-9999.0, 4.0])
        result = apply_derivation(
            {"x": df_x}, formula="log(x)",
            stop_on_gaps=False, stop_on_error=True,
            input_no_data_values={"x": -9999.0}, output_no_data_value=-9999.0,
        )
        assert len(result) == 2
        assert result[RESULT_COL].tolist() == pytest.approx([-9999.0, np.log(4.0)])
