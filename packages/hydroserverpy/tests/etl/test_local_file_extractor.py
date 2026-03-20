import pytest
from unittest.mock import MagicMock, patch

from hydroserverpy.etl.extractors.local import LocalFileExtractor
from hydroserverpy.etl.exceptions import ETLError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def extractor():
    return LocalFileExtractor(source_uri="/data/test_file.csv")


@pytest.fixture
def templated_extractor():
    return LocalFileExtractor(source_uri="/data/{filename}")


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

class TestLocalFileExtractorModel:

    def test_source_uri_is_stored(self, extractor):
        assert extractor.source_uri == "/data/test_file.csv"

    def test_source_uri_is_a_template_field(self):
        field = LocalFileExtractor.model_fields["source_uri"]
        assert field.json_schema_extra.get("template") is True

    def test_source_uri_is_required(self):
        with pytest.raises(Exception):
            LocalFileExtractor()  # noqa

    def test_templated_source_uri_accepted(self, templated_extractor):
        assert "{filename}" in templated_extractor.source_uri


# ---------------------------------------------------------------------------
# LocalFileExtractor.extract – successful responses
# ---------------------------------------------------------------------------

class TestLocalFileExtractorSuccess:

    def test_returns_text_file_handle(self, extractor, tmp_path):
        test_file = tmp_path / "test_file.csv"
        test_file.write_text("col1,col2\n1,2\n")
        extractor.source_uri = str(test_file)

        result = extractor.extract()

        assert hasattr(result, "read")
        assert hasattr(result, "seek")
        assert not isinstance(result, bytes)
        result.close()

    def test_returned_file_handle_is_seeked_to_zero(self, extractor, tmp_path):
        test_file = tmp_path / "test_file.csv"
        test_file.write_text("col1,col2\n1,2\n")
        extractor.source_uri = str(test_file)

        result = extractor.extract()

        assert result.tell() == 0
        result.close()

    def test_file_handle_contains_correct_content(self, extractor, tmp_path):
        content = "col1,col2\n1,2\n3,4\n"
        test_file = tmp_path / "test_file.csv"
        test_file.write_text(content)
        extractor.source_uri = str(test_file)

        result = extractor.extract()

        assert result.read() == content
        result.close()

    def test_open_called_with_correct_path(self, extractor, tmp_path):
        test_file = tmp_path / "test_file.csv"
        test_file.write_text("data")
        extractor.source_uri = str(test_file)

        with patch("builtins.open", wraps=open) as mock_file:
            result = extractor.extract()
            result.close()

        mock_file.assert_called_once_with(str(test_file), "r")

    def test_open_called_in_text_mode(self, extractor, tmp_path):
        test_file = tmp_path / "test_file.csv"
        test_file.write_text("data")
        extractor.source_uri = str(test_file)

        with patch("builtins.open", wraps=open) as mock_file:
            result = extractor.extract()
            result.close()

        assert "r" in mock_file.call_args.args

    def test_template_uri_is_rendered_before_open(self, templated_extractor, tmp_path):
        test_file = tmp_path / "mydata.csv"
        test_file.write_text("data")
        templated_extractor.source_uri = str(tmp_path / "{filename}")

        with patch("builtins.open", wraps=open) as mock_file:
            result = templated_extractor.extract(filename="mydata.csv")
            result.close()

        mock_file.assert_called_once_with(str(test_file), "r")


# ---------------------------------------------------------------------------
# LocalFileExtractor.extract – error handling
# ---------------------------------------------------------------------------

class TestLocalFileExtractorErrors:

    def test_file_not_found_raises_etl_error(self, extractor):
        extractor.source_uri = "/nonexistent/path/file.csv"

        with pytest.raises(ETLError, match="not found"):
            extractor.extract()

    def test_file_not_found_includes_uri(self, extractor):
        extractor.source_uri = "/nonexistent/path/file.csv"

        with pytest.raises(ETLError, match="/nonexistent/path/file.csv"):
            extractor.extract()

    def test_file_not_found_chains_original_exception(self, extractor):
        extractor.source_uri = "/nonexistent/path/file.csv"

        with pytest.raises(ETLError) as exc_info:
            extractor.extract()

        assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    @pytest.mark.parametrize("exc", [
        PermissionError("Permission denied"),
        OSError("some OS error"),
    ])
    def test_open_failure_raises_etl_error(self, extractor, exc):
        with patch("builtins.open", side_effect=exc):
            with pytest.raises(ETLError, match="Failed to open"):
                extractor.extract()

    @pytest.mark.parametrize("exc", [
        PermissionError("Permission denied"),
        OSError("some OS error"),
    ])
    def test_open_failure_includes_uri(self, extractor, exc):
        with patch("builtins.open", side_effect=exc):
            with pytest.raises(ETLError, match="/data/test_file.csv"):
                extractor.extract()

    @pytest.mark.parametrize("exc", [
        PermissionError("Permission denied"),
        OSError("some OS error"),
    ])
    def test_open_failure_chains_original_exception(self, extractor, exc):
        with patch("builtins.open", side_effect=exc):
            with pytest.raises(ETLError) as exc_info:
                extractor.extract()

        assert exc_info.value.__cause__ is exc

    def test_empty_file_raises_etl_error(self, extractor, tmp_path):
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("")
        extractor.source_uri = str(empty_file)

        with pytest.raises(ETLError, match="empty"):
            extractor.extract()

    def test_empty_file_includes_uri(self, extractor, tmp_path):
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("")
        extractor.source_uri = str(empty_file)

        with pytest.raises(ETLError, match=str(empty_file)):
            extractor.extract()

    def test_empty_file_handle_is_closed(self, extractor):
        handle = MagicMock()
        handle.read.return_value = ""

        with patch("builtins.open", return_value=handle):
            with pytest.raises(ETLError):
                extractor.extract()

        handle.close.assert_called_once()

    def test_missing_template_variable_raises_value_error(self, templated_extractor):
        with pytest.raises(ValueError, match="Missing required runtime variables"):
            templated_extractor.extract()
