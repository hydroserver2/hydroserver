import pytest
import numpy as np
import pandas as pd
from datetime import timezone
from unittest.mock import patch

from hydroserverpy.etl.transformers.base import Transformer, ETLDataMapping, ETLTargetPath
from hydroserverpy.etl.operations.arithmetic_expression import ArithmeticExpressionOperation
from hydroserverpy.etl.exceptions import ETLError


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _make_transformer(**kwargs):
    """Instantiate a concrete Transformer subclass for testing."""

    class ConcreteTransformer(Transformer):
        def transform(self, payload, data_mappings, **kwargs):
            pass

    defaults = dict(timestamp_key="timestamp")
    defaults.update(kwargs)
    return ConcreteTransformer(**defaults)


def _make_mapping(source_id, target_id, operations=None):
    target_path = ETLTargetPath(
        target_identifier=target_id,
        data_operations=operations or [],
    )
    return ETLDataMapping(source_identifier=source_id, target_paths=[target_path])


def _make_long_df(target_id="target_1", timestamps=None, values=None):
    """Build a minimal long-format (timestamp, value, target_id) DataFrame."""
    if timestamps is None:
        timestamps = ["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"]
    if values is None:
        values = [1.0, 2.0]
    return pd.DataFrame({
        "timestamp": timestamps,
        "value": values,
        "target_id": target_id,
    })


def _make_tv_df(timestamps, values):
    """Build a (timestamp, value) DataFrame for use in apply_data_transformations tests."""
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps, utc=True),
        "value": values,
    })


def _make_expr_op(expression, target_identifier="target_1"):
    """Create a real ArithmeticExpressionOperation for use in ETLTargetPath."""
    return ArithmeticExpressionOperation(
        expression=expression,
        target_identifier=target_identifier,
    )


# ---------------------------------------------------------------------------
# standardize_dataframe – timestamp handling
# ---------------------------------------------------------------------------

class TestStandardizeDataframeTimestamp:

    def test_missing_timestamp_column_raises_etl_error(self):
        transformer = _make_transformer(timestamp_key="ts")
        df = pd.DataFrame([{"value": 1.0, "target_id": "target_1"}])
        mapping = _make_mapping("value", "target_1")

        with pytest.raises(ETLError):
            transformer.standardize_dataframe(df, [mapping])

    def test_timestamp_column_is_parsed_to_utc(self):
        transformer = _make_transformer()
        df = _make_long_df()
        mapping = _make_mapping("value", "target_1")

        result = transformer.standardize_dataframe(df, [mapping])

        assert result["timestamp"].dt.tz == timezone.utc

    def test_duplicate_timestamps_are_deduplicated_per_target(self):
        transformer = _make_transformer()
        df = pd.DataFrame({
            "timestamp": ["2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z"],
            "value": [1.0, 2.0],
            "target_id": "target_1",
        })
        mapping = _make_mapping("value", "target_1")

        result = transformer.standardize_dataframe(df, [mapping])

        assert len(result[result["target_id"] == "target_1"]) == 1

    def test_last_duplicate_timestamp_is_kept(self):
        transformer = _make_transformer()
        df = pd.DataFrame({
            "timestamp": ["2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z"],
            "value": [1.0, 2.0],
            "target_id": "target_1",
        })
        mapping = _make_mapping("value", "target_1")

        result = transformer.standardize_dataframe(df, [mapping])

        assert result[result["target_id"] == "target_1"]["value"].iloc[0] == 2.0

    def test_deduplication_is_per_target_not_global(self):
        # Same timestamp for two different targets should not be deduplicated across targets
        transformer = _make_transformer()
        df = pd.DataFrame({
            "timestamp": ["2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z"],
            "value": [1.0, 2.0],
            "target_id": ["target_1", "target_2"],
        })
        mappings = [_make_mapping("value", "target_1"), _make_mapping("value", "target_2")]

        result = transformer.standardize_dataframe(df, mappings)

        assert len(result) == 2


# ---------------------------------------------------------------------------
# standardize_dataframe – output structure
# ---------------------------------------------------------------------------

class TestStandardizeDataframeOutput:

    def test_result_contains_timestamp_column(self):
        transformer = _make_transformer()
        df = _make_long_df()
        mapping = _make_mapping("value", "target_1")

        result = transformer.standardize_dataframe(df, [mapping])

        assert "timestamp" in result.columns

    def test_result_contains_value_column(self):
        transformer = _make_transformer()
        df = _make_long_df()
        mapping = _make_mapping("value", "target_1")

        result = transformer.standardize_dataframe(df, [mapping])

        assert "value" in result.columns

    def test_result_contains_target_id_column(self):
        transformer = _make_transformer()
        df = _make_long_df()
        mapping = _make_mapping("value", "target_1")

        result = transformer.standardize_dataframe(df, [mapping])

        assert "target_id" in result.columns

    def test_target_id_values_are_strings(self):
        transformer = _make_transformer()
        df = _make_long_df()
        mapping = _make_mapping("value", "target_1")

        result = transformer.standardize_dataframe(df, [mapping])

        assert pd.api.types.is_string_dtype(result["target_id"])
        assert result["target_id"].iloc[0] == "target_1"

    def test_result_has_correct_row_count(self):
        transformer = _make_transformer()
        df = _make_long_df()
        mapping = _make_mapping("value", "target_1")

        result = transformer.standardize_dataframe(df, [mapping])

        assert len(result) == 2

    def test_multiple_targets_all_present_in_output(self):
        transformer = _make_transformer()
        df = pd.concat([
            _make_long_df("target_1"),
            _make_long_df("target_2"),
        ], ignore_index=True)
        mappings = [_make_mapping("value", "target_1"), _make_mapping("value", "target_2")]

        result = transformer.standardize_dataframe(df, mappings)

        assert set(result["target_id"].unique()) == {"target_1", "target_2"}
        assert len(result) == 4

    def test_empty_dataframe_returns_empty_result_with_correct_columns(self):
        transformer = _make_transformer()
        df = pd.DataFrame(columns=["timestamp", "value", "target_id"])
        mapping = _make_mapping("value", "target_1")

        result = transformer.standardize_dataframe(df, [mapping])

        assert result.empty
        assert set(result.columns) == {"timestamp", "value", "target_id"}

    def test_values_are_correct_per_target(self):
        transformer = _make_transformer()
        df = pd.concat([
            _make_long_df("target_1", values=[1.0, 2.0]),
            _make_long_df("target_2", values=[10.0, 20.0]),
        ], ignore_index=True)
        mappings = [_make_mapping("value", "target_1"), _make_mapping("value", "target_2")]

        result = transformer.standardize_dataframe(df, mappings)

        t1 = result[result["target_id"] == "target_1"].sort_values("timestamp")
        t2 = result[result["target_id"] == "target_2"].sort_values("timestamp")
        assert t1["value"].tolist() == pytest.approx([1.0, 2.0])
        assert t2["value"].tolist() == pytest.approx([10.0, 20.0])

    def test_target_with_no_matching_mapping_is_passed_through(self):
        # A target_id in the DataFrame with no matching path in data_mappings
        # should still appear in output with no operations applied.
        transformer = _make_transformer()
        df = _make_long_df("unmapped_target")
        mapping = _make_mapping("value", "other_target")

        result = transformer.standardize_dataframe(df, [mapping])

        assert "unmapped_target" in result["target_id"].values


# ---------------------------------------------------------------------------
# resolve_source_column
# ---------------------------------------------------------------------------

class TestResolveSourceColumn:

    def test_resolves_string_column_name(self):
        df = pd.DataFrame({"value": [1.0], "other": [2.0]})

        result = Transformer.resolve_source_column(df, "value")

        assert result == "value"

    def test_resolves_integer_as_positional_index(self):
        df = pd.DataFrame({"a": [1.0], "b": [2.0], "c": [3.0]})

        result = Transformer.resolve_source_column(df, 1)

        assert result == "b"

    def test_integer_label_takes_precedence_over_positional_index(self):
        df = pd.DataFrame({0: [1.0], 1: [2.0], 2: [3.0]})

        result = Transformer.resolve_source_column(df, 1)

        assert result == 1

    def test_missing_string_column_raises_etl_error(self):
        df = pd.DataFrame({"value": [1.0]})

        with pytest.raises(ETLError, match="nonexistent"):
            Transformer.resolve_source_column(df, "nonexistent")

    def test_missing_string_column_error_includes_column_name(self):
        df = pd.DataFrame({"value": [1.0]})

        with pytest.raises(ETLError, match="nonexistent"):
            Transformer.resolve_source_column(df, "nonexistent")

    def test_out_of_range_integer_index_raises_etl_error(self):
        df = pd.DataFrame({"a": [1.0], "b": [2.0]})

        with pytest.raises(ETLError, match="out of range"):
            Transformer.resolve_source_column(df, 99)

    def test_out_of_range_integer_index_error_chains_index_error(self):
        df = pd.DataFrame({"a": [1.0], "b": [2.0]})

        with pytest.raises(ETLError) as exc_info:
            Transformer.resolve_source_column(df, 99)

        assert isinstance(exc_info.value.__cause__, IndexError)

    def test_zero_index_resolves_to_first_column(self):
        df = pd.DataFrame({"first": [1.0], "second": [2.0]})

        result = Transformer.resolve_source_column(df, 0)

        assert result == "first"


# ---------------------------------------------------------------------------
# apply_data_transformations
# ---------------------------------------------------------------------------

class TestApplyDataTransformations:

    def test_returns_dataframe_unchanged_when_no_operations(self):
        df = _make_tv_df(["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"], [1.0, 2.0])
        path = ETLTargetPath(target_identifier="target_1", data_operations=[])

        result = Transformer.apply_data_transformations(df, path)

        pd.testing.assert_frame_equal(result, df)

    def test_result_has_timestamp_and_value_columns(self):
        df = _make_tv_df(["2024-01-01T00:00:00Z"], [1.0])
        path = ETLTargetPath(target_identifier="target_1", data_operations=[])

        result = Transformer.apply_data_transformations(df, path)

        assert "timestamp" in result.columns
        assert "value" in result.columns

    def test_coerces_string_value_column_to_numeric(self):
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(
                ["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z", "2024-01-03T00:00:00Z"],
                utc=True,
            ),
            "value": pd.Series(["1.0", "2.0", "3.0"]),
        })
        path = ETLTargetPath(target_identifier="target_1", data_operations=[])

        result = Transformer.apply_data_transformations(df, path)

        assert result["value"].dtype != "object"
        assert result["value"].tolist() == [1.0, 2.0, 3.0]

    def test_non_numeric_strings_coerced_to_nan(self):
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(
                ["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z", "2024-01-03T00:00:00Z"],
                utc=True,
            ),
            "value": pd.Series(["1.0", "bad", "3.0"]),
        })
        path = ETLTargetPath(target_identifier="target_1", data_operations=[])

        result = Transformer.apply_data_transformations(df, path)

        assert np.isnan(result["value"].iloc[1])

    def test_numeric_dtype_is_not_coerced(self):
        df = _make_tv_df(["2024-01-01T00:00:00Z"], [1.0])
        path = ETLTargetPath(target_identifier="target_1", data_operations=[])

        with patch("hydroserverpy.etl.transformers.base.pd.to_numeric") as mock_coerce:
            Transformer.apply_data_transformations(df, path)

        mock_coerce.assert_not_called()

    def test_operation_apply_is_called(self):
        # Uses identity expression "x" to verify the operation is invoked and its result returned.
        df = _make_tv_df(["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"], [1.0, 2.0])
        path = ETLTargetPath(
            target_identifier="target_1",
            data_operations=[_make_expr_op("x")],
        )

        result = Transformer.apply_data_transformations(df, path)

        pd.testing.assert_series_equal(result["value"], df["value"])

    def test_operations_are_applied_in_order(self):
        # x * 2 then x + 10 on input 1.0 should give (1*2)+10 = 12.
        # If reversed: (1+10)*2 = 22. The distinct expected values confirm ordering.
        df = _make_tv_df(["2024-01-01T00:00:00Z"], [1.0])
        path = ETLTargetPath(
            target_identifier="target_1",
            data_operations=[
                _make_expr_op("x * 2"),
                _make_expr_op("x + 10"),
            ],
        )

        result = Transformer.apply_data_transformations(df, path)

        assert result["value"].iloc[0] == pytest.approx(12.0)

    def test_output_of_one_operation_is_input_to_next(self):
        # x * 2 then x * 3 on input 1.0 should give (1*2)*3 = 6.
        # If chaining is broken and both receive the original: (1*3) = 3.
        df = _make_tv_df(["2024-01-01T00:00:00Z"], [1.0])
        path = ETLTargetPath(
            target_identifier="target_1",
            data_operations=[
                _make_expr_op("x * 2"),
                _make_expr_op("x * 3"),
            ],
        )

        result = Transformer.apply_data_transformations(df, path)

        assert result["value"].iloc[0] == pytest.approx(6.0)


# ---------------------------------------------------------------------------
# wide_to_long
# ---------------------------------------------------------------------------

class TestWideToLong:

    def _make_wide_df(self, timestamps, **columns):
        """Build a wide-format DataFrame with a timestamp column and one column per source."""
        data = {"timestamp": pd.to_datetime(timestamps, utc=True)}
        data.update(columns)
        return pd.DataFrame(data)

    def test_returns_dataframe(self):
        df = self._make_wide_df(["2024-01-01T00:00:00Z"], col_a=[1.0])
        mapping = _make_mapping("col_a", "target_1")
        result = Transformer.reshape_dataframe_wide_to_long(df, [mapping])
        assert isinstance(result, pd.DataFrame)

    def test_result_has_timestamp_value_target_id_columns(self):
        df = self._make_wide_df(["2024-01-01T00:00:00Z"], col_a=[1.0])
        mapping = _make_mapping("col_a", "target_1")
        result = Transformer.reshape_dataframe_wide_to_long(df, [mapping])
        assert set(result.columns) == {"timestamp", "value", "target_id"}

    def test_single_mapping_produces_correct_target_id(self):
        df = self._make_wide_df(["2024-01-01T00:00:00Z"], col_a=[1.0])
        mapping = _make_mapping("col_a", "target_1")
        result = Transformer.reshape_dataframe_wide_to_long(df, [mapping])
        assert result["target_id"].iloc[0] == "target_1"

    def test_target_id_values_are_strings(self):
        df = self._make_wide_df(["2024-01-01T00:00:00Z"], col_a=[1.0])
        mapping = _make_mapping("col_a", 42)
        result = Transformer.reshape_dataframe_wide_to_long(df, [mapping])
        assert result["target_id"].iloc[0] == "42"

    def test_values_are_taken_from_source_column(self):
        df = self._make_wide_df(["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"], col_a=[3.0, 7.0])
        mapping = _make_mapping("col_a", "target_1")
        result = Transformer.reshape_dataframe_wide_to_long(df, [mapping])
        assert list(result["value"]) == [3.0, 7.0]

    def test_timestamps_are_preserved(self):
        ts = ["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"]
        df = self._make_wide_df(ts, col_a=[1.0, 2.0])
        mapping = _make_mapping("col_a", "target_1")
        result = Transformer.reshape_dataframe_wide_to_long(df, [mapping])
        assert list(result["timestamp"]) == list(pd.to_datetime(ts, utc=True))

    def test_multiple_source_columns_produce_rows_for_each_target(self):
        df = self._make_wide_df(["2024-01-01T00:00:00Z"], col_a=[1.0], col_b=[2.0])
        mappings = [_make_mapping("col_a", "target_1"), _make_mapping("col_b", "target_2")]
        result = Transformer.reshape_dataframe_wide_to_long(df, mappings)
        assert set(result["target_id"].unique()) == {"target_1", "target_2"}

    def test_one_to_many_mapping_produces_rows_for_each_target(self):
        df = self._make_wide_df(["2024-01-01T00:00:00Z"], col_a=[5.0])
        mapping = ETLDataMapping(
            source_identifier="col_a",
            target_paths=[
                ETLTargetPath(target_identifier="target_1", data_operations=[]),
                ETLTargetPath(target_identifier="target_2", data_operations=[]),
            ],
        )
        result = Transformer.reshape_dataframe_wide_to_long(df, [mapping])
        assert set(result["target_id"].unique()) == {"target_1", "target_2"}
        assert result[result["target_id"] == "target_1"]["value"].iloc[0] == 5.0
        assert result[result["target_id"] == "target_2"]["value"].iloc[0] == 5.0

    def test_row_count_is_n_timestamps_times_n_targets(self):
        df = self._make_wide_df(
            ["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"],
            col_a=[1.0, 2.0],
            col_b=[3.0, 4.0],
        )
        mappings = [_make_mapping("col_a", "target_1"), _make_mapping("col_b", "target_2")]
        result = Transformer.reshape_dataframe_wide_to_long(df, mappings)
        assert len(result) == 4  # 2 timestamps × 2 targets

    def test_empty_mappings_returns_empty_dataframe(self):
        df = self._make_wide_df(["2024-01-01T00:00:00Z"], col_a=[1.0])
        result = Transformer.reshape_dataframe_wide_to_long(df, [])
        assert result.empty
        assert set(result.columns) == {"timestamp", "value", "target_id"}

    def test_source_column_not_in_df_raises_etl_error(self):
        df = self._make_wide_df(["2024-01-01T00:00:00Z"], col_a=[1.0])
        mapping = _make_mapping("missing_col", "target_1")
        with pytest.raises(ETLError):
            Transformer.reshape_dataframe_wide_to_long(df, [mapping])
