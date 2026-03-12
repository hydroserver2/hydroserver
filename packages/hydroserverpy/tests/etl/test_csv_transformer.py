import pytest
import textwrap
from io import BytesIO, StringIO

from hydroserverpy.etl.transformers.base import ETLDataMapping, ETLTargetPath
from hydroserverpy.etl.transformers.csv import CSVTransformer
from hydroserverpy.etl.exceptions import ETLError


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _make_transformer(**kwargs):
    defaults = dict(timestamp_key="timestamp")
    defaults.update(kwargs)
    return CSVTransformer(**defaults)


def _make_mapping(source_id, target_id):
    return ETLDataMapping(
        source_identifier=source_id,
        target_paths=[ETLTargetPath(target_identifier=target_id, data_operations=[])],
    )


def _csv(content):
    """Return a dedented CSV string."""
    return textwrap.dedent(content).lstrip()


def _csv_bytes(content):
    return BytesIO(_csv(content).encode())


def _csv_stringio(content):
    return StringIO(_csv(content))


def _targets(result, target_id):
    """Return rows for a specific target_id, sorted by timestamp."""
    return result[result["target_id"] == str(target_id)].sort_values("timestamp")


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

class TestCSVTransformerModel:

    def test_default_delimiter_is_comma(self):
        t = _make_transformer()
        assert t.delimiter == ","

    def test_default_identifier_type_is_name(self):
        t = _make_transformer()
        assert t.identifier_type == "name"

    def test_default_data_start_row_is_1(self):
        t = _make_transformer()
        assert t.data_start_row == 1

    def test_default_header_row_is_none(self):
        t = _make_transformer()
        assert t.header_row is None

    def test_timestamp_key_is_required(self):
        with pytest.raises(Exception):
            CSVTransformer()  # noqa

    def test_custom_delimiter_is_stored(self):
        t = _make_transformer(delimiter="|")
        assert t.delimiter == "|"

    @pytest.mark.parametrize("delimiter", [",", "|", "\t", ";", " "])
    def test_valid_delimiters_are_accepted(self, delimiter):
        t = _make_transformer(delimiter=delimiter)
        assert t.delimiter == delimiter

    def test_invalid_delimiter_raises_error(self):
        with pytest.raises(Exception):
            _make_transformer(delimiter="x")


class TestCSVTransformerValidateTimestampKey:

    def test_non_integer_timestamp_key_raises_in_index_mode(self):
        with pytest.raises(ValueError, match="must be an integer"):
            _make_transformer(identifier_type="index", timestamp_key="ts")

    def test_zero_timestamp_key_raises_in_index_mode(self):
        with pytest.raises(ValueError, match="greater than 0"):
            _make_transformer(identifier_type="index", timestamp_key="0")

    def test_negative_timestamp_key_raises_in_index_mode(self):
        with pytest.raises(ValueError, match="greater than 0"):
            _make_transformer(identifier_type="index", timestamp_key="-1")

    def test_valid_integer_timestamp_key_accepted_in_index_mode(self):
        t = _make_transformer(identifier_type="index", timestamp_key="1")
        assert t.timestamp_key == "1"

    def test_string_timestamp_key_accepted_in_name_mode(self):
        t = _make_transformer(identifier_type="name", timestamp_key="ts")
        assert t.timestamp_key == "ts"


class TestCSVTransformerValidateDataStartRow:

    def test_data_start_row_equal_to_header_row_raises(self):
        with pytest.raises(ValueError, match="greater than the header row"):
            _make_transformer(header_row=2, data_start_row=2)

    def test_data_start_row_less_than_header_row_raises(self):
        with pytest.raises(ValueError, match="greater than the header row"):
            _make_transformer(header_row=3, data_start_row=2)

    def test_data_start_row_greater_than_header_row_accepted(self):
        t = _make_transformer(header_row=1, data_start_row=2)
        assert t.data_start_row == 2

    def test_data_start_row_without_header_row_accepted(self):
        t = _make_transformer(header_row=None, data_start_row=3)
        assert t.data_start_row == 3


# ---------------------------------------------------------------------------
# transform – payload type validation
# ---------------------------------------------------------------------------

class TestCSVTransformerPayloadTypeValidation:

    def test_invalid_payload_type_raises_etl_error(self):
        t = _make_transformer()
        with pytest.raises(ETLError, match="payload object of type"):
            t.transform(12345, [_make_mapping("value", "target_1")])  # noqa

    def test_invalid_payload_type_error_includes_type_name(self):
        t = _make_transformer()
        with pytest.raises(ETLError, match="int"):
            t.transform(12345, [_make_mapping("value", "target_1")])  # noqa

    def test_str_payload_is_accepted(self):
        t = _make_transformer()
        csv = _csv("timestamp,value\n2024-01-01T00:00:00Z,1.0\n")
        result = t.transform(csv, [_make_mapping("value", "target_1")])
        assert not result.empty

    def test_bytes_payload_is_accepted(self):
        t = _make_transformer()
        csv = _csv("timestamp,value\n2024-01-01T00:00:00Z,1.0\n").encode()
        result = t.transform(csv, [_make_mapping("value", "target_1")])
        assert not result.empty

    def test_bytesio_payload_is_accepted(self):
        t = _make_transformer()
        result = t.transform(
            _csv_bytes("timestamp,value\n2024-01-01T00:00:00Z,1.0\n"),
            [_make_mapping("value", "target_1")],
        )
        assert not result.empty

    def test_stringio_payload_is_accepted(self):
        t = _make_transformer()
        result = t.transform(
            _csv_stringio("timestamp,value\n2024-01-01T00:00:00Z,1.0\n"),
            [_make_mapping("value", "target_1")],
        )
        assert not result.empty


# ---------------------------------------------------------------------------
# transform – output structure
# ---------------------------------------------------------------------------

class TestCSVTransformerOutputStructure:

    def test_result_contains_timestamp_column(self):
        t = _make_transformer()
        csv = _csv("timestamp,value\n2024-01-01T00:00:00Z,1.0\n")
        result = t.transform(csv, [_make_mapping("value", "target_1")])
        assert "timestamp" in result.columns

    def test_result_contains_value_column(self):
        t = _make_transformer()
        csv = _csv("timestamp,value\n2024-01-01T00:00:00Z,1.0\n")
        result = t.transform(csv, [_make_mapping("value", "target_1")])
        assert "value" in result.columns

    def test_result_contains_target_id_column(self):
        t = _make_transformer()
        csv = _csv("timestamp,value\n2024-01-01T00:00:00Z,1.0\n")
        result = t.transform(csv, [_make_mapping("value", "target_1")])
        assert "target_id" in result.columns

    def test_result_has_only_three_columns(self):
        t = _make_transformer()
        csv = _csv("timestamp,value\n2024-01-01T00:00:00Z,1.0\n")
        result = t.transform(csv, [_make_mapping("value", "target_1")])
        assert set(result.columns) == {"timestamp", "value", "target_id"}

    def test_target_id_values_are_strings(self):
        t = _make_transformer()
        csv = _csv("timestamp,value\n2024-01-01T00:00:00Z,1.0\n")
        result = t.transform(csv, [_make_mapping("value", "target_1")])
        assert result["target_id"].iloc[0] == "target_1"


# ---------------------------------------------------------------------------
# transform – name mode
# ---------------------------------------------------------------------------

class TestCSVTransformerNameMode:

    def test_correct_row_count(self):
        t = _make_transformer()
        csv = _csv("""
            timestamp,value
            2024-01-01T00:00:00Z,1.0
            2024-01-02T00:00:00Z,2.0
            2024-01-03T00:00:00Z,3.0
        """)
        result = t.transform(csv, [_make_mapping("value", "target_1")])
        assert len(_targets(result, "target_1")) == 3

    def test_pipe_delimiter(self):
        t = _make_transformer(delimiter="|")
        csv = _csv("timestamp|value\n2024-01-01T00:00:00Z|1.0\n")
        result = t.transform(csv, [_make_mapping("value", "target_1")])
        assert "target_1" in result["target_id"].values

    def test_tab_delimiter(self):
        t = _make_transformer(delimiter="\t")
        csv = _csv("timestamp\tvalue\n2024-01-01T00:00:00Z\t1.0\n")
        result = t.transform(csv, [_make_mapping("value", "target_1")])
        assert "target_1" in result["target_id"].values

    def test_custom_timestamp_key(self):
        t = _make_transformer(timestamp_key="ts")
        csv = _csv("ts,value\n2024-01-01T00:00:00Z,1.0\n")
        result = t.transform(csv, [_make_mapping("value", "target_1")])
        assert "timestamp" in result.columns

    def test_header_row_skips_preceding_rows(self):
        t = _make_transformer(header_row=2, data_start_row=3)
        csv = _csv("""
            metadata line
            timestamp,value
            2024-01-01T00:00:00Z,1.0
        """)
        result = t.transform(csv, [_make_mapping("value", "target_1")])
        assert "target_1" in result["target_id"].values
        assert len(_targets(result, "target_1")) == 1

    def test_data_start_row_skips_header_rows(self):
        t = _make_transformer(identifier_type="index", timestamp_key="1", data_start_row=3)
        csv = _csv("""
            skip this row
            skip this row too
            2024-01-01T00:00:00Z,1.0
            2024-01-02T00:00:00Z,2.0
        """)
        result = t.transform(csv, [_make_mapping("2", "target_1")])
        assert len(_targets(result, "target_1")) == 2

    def test_missing_column_raises_etl_error(self):
        t = _make_transformer()
        csv = _csv("timestamp,value\n2024-01-01T00:00:00Z,1.0\n")
        with pytest.raises(ETLError, match="not found"):
            t.transform(csv, [_make_mapping("nonexistent", "target_1")])

    def test_empty_csv_raises_etl_error(self):
        t = _make_transformer()
        with pytest.raises(ETLError, match="empty"):
            t.transform("", [_make_mapping("value", "target_1")])

    def test_multiple_mappings_produce_rows_for_each_target(self):
        t = _make_transformer()
        csv = _csv("timestamp,val_a,val_b\n2024-01-01T00:00:00Z,1.0,2.0\n")
        result = t.transform(csv, [
            _make_mapping("val_a", "target_1"),
            _make_mapping("val_b", "target_2"),
        ])
        assert set(result["target_id"].unique()) == {"target_1", "target_2"}

    def test_one_to_many_mapping_produces_rows_for_each_target(self):
        t = _make_transformer()
        csv = _csv("timestamp,value\n2024-01-01T00:00:00Z,1.0\n2024-01-02T00:00:00Z,2.0\n")
        mapping = ETLDataMapping(
            source_identifier="value",
            target_paths=[
                ETLTargetPath(target_identifier="target_1", data_operations=[]),
                ETLTargetPath(target_identifier="target_2", data_operations=[]),
            ],
        )
        result = t.transform(csv, [mapping])
        assert set(result["target_id"].unique()) == {"target_1", "target_2"}
        assert len(_targets(result, "target_1")) == 2
        assert len(_targets(result, "target_2")) == 2

    def test_values_are_correct_per_target(self):
        t = _make_transformer()
        csv = _csv("""
            timestamp,val_a,val_b
            2024-01-01T00:00:00Z,1.0,10.0
            2024-01-02T00:00:00Z,2.0,20.0
        """)
        result = t.transform(csv, [
            _make_mapping("val_a", "target_1"),
            _make_mapping("val_b", "target_2"),
        ])
        assert _targets(result, "target_1")["value"].tolist() == pytest.approx([1.0, 2.0])
        assert _targets(result, "target_2")["value"].tolist() == pytest.approx([10.0, 20.0])


# ---------------------------------------------------------------------------
# transform – index mode
# ---------------------------------------------------------------------------

class TestCSVTransformerIndexMode:

    def test_result_contains_timestamp_column(self):
        t = _make_transformer(identifier_type="index", timestamp_key="1")
        csv = _csv("2024-01-01T00:00:00Z,1.0\n2024-01-02T00:00:00Z,2.0\n")
        result = t.transform(csv, [_make_mapping("2", "target_1")])
        assert "timestamp" in result.columns

    def test_result_contains_target_id(self):
        t = _make_transformer(identifier_type="index", timestamp_key="1")
        csv = _csv("2024-01-01T00:00:00Z,1.0\n2024-01-02T00:00:00Z,2.0\n")
        result = t.transform(csv, [_make_mapping("2", "target_1")])
        assert "target_1" in result["target_id"].values

    def test_non_integer_source_identifier_raises_etl_error(self):
        t = _make_transformer(identifier_type="index", timestamp_key="1")
        csv = _csv("2024-01-01T00:00:00Z,1.0\n")
        with pytest.raises(ETLError, match="must be integers"):
            t.transform(csv, [_make_mapping("not_an_int", "target_1")])

    def test_zero_source_identifier_raises_etl_error(self):
        t = _make_transformer(identifier_type="index", timestamp_key="1")
        csv = _csv("2024-01-01T00:00:00Z,1.0\n")
        with pytest.raises(ETLError, match="greater than 0"):
            t.transform(csv, [_make_mapping("0", "target_1")])

    def test_out_of_range_index_raises_etl_error(self):
        t = _make_transformer(identifier_type="index", timestamp_key="1")
        csv = _csv("2024-01-01T00:00:00Z,1.0\n")
        with pytest.raises(ETLError):
            t.transform(csv, [_make_mapping("99", "target_1")])

    def test_columns_are_relabelled_as_1_based_strings(self):
        """Index mode must relabel columns so resolve_source_column can match string source identifiers."""
        t = _make_transformer(identifier_type="index", timestamp_key="1")
        csv = _csv("2024-01-01T00:00:00Z,1.0\n2024-01-02T00:00:00Z,2.0\n")
        # If relabelling is broken, resolve_source_column will raise an ETLError
        result = t.transform(csv, [_make_mapping("2", "target_1")])
        assert "target_1" in result["target_id"].values


# ---------------------------------------------------------------------------
# strip_comments
# ---------------------------------------------------------------------------

class TestCSVTransformerStripComments:

    def test_removes_comment_lines_from_str(self):
        csv = _csv("""
            # comment
            timestamp,value
            2024-01-01T00:00:00Z,1.0
        """)
        result = CSVTransformer.strip_comments(csv)
        assert "#" not in result.read()

    def test_preserves_data_lines_from_str(self):
        csv = _csv("# comment\ntimestamp,value\n2024-01-01T00:00:00Z,1.0\n")
        result = CSVTransformer.strip_comments(csv)
        content = result.read()
        assert "timestamp,value" in content
        assert "2024-01-01T00:00:00Z,1.0" in content

    def test_removes_comment_lines_from_bytesio(self):
        csv = _csv_bytes("# comment\ntimestamp,value\n2024-01-01T00:00:00Z,1.0\n")
        result = CSVTransformer.strip_comments(csv)
        assert "#" not in result.read()

    def test_preserves_data_lines_from_bytesio(self):
        csv = _csv_bytes("# comment\ntimestamp,value\n2024-01-01T00:00:00Z,1.0\n")
        result = CSVTransformer.strip_comments(csv)
        content = result.read()
        assert "timestamp,value" in content

    def test_removes_indented_comment_lines(self):
        csv = _csv("   # indented comment\ntimestamp,value\n2024-01-01T00:00:00Z,1.0\n")
        result = CSVTransformer.strip_comments(csv)
        assert "#" not in result.read()

    def test_returns_stringio(self):
        result = CSVTransformer.strip_comments("timestamp,value\n")
        assert isinstance(result, StringIO)

    def test_no_comments_returns_content_unchanged(self):
        csv = "timestamp,value\n2024-01-01T00:00:00Z,1.0\n"
        result = CSVTransformer.strip_comments(csv)
        assert result.read() == csv

    def test_all_comment_lines_returns_empty_stringio(self):
        csv = "# line 1\n# line 2\n"
        result = CSVTransformer.strip_comments(csv)
        assert result.read() == ""

    def test_hash_in_data_value_is_preserved(self):
        csv = "timestamp,label\n2024-01-01T00:00:00Z,value#1\n"
        result = CSVTransformer.strip_comments(csv)
        assert "value#1" in result.read()
