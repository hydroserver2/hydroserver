import pytest
from io import BytesIO
from unittest.mock import MagicMock, patch

import requests

from hydroserverpy.etl.extractors.http import HTTPExtractor
from hydroserverpy.etl.exceptions import ETLError


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _make_response(status_code=200, chunks=None, headers=None):
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {"Content-Type": "text/csv"}
    response.iter_content.return_value = iter(chunks if chunks is not None else [b"data chunk"])
    return response


@pytest.fixture
def extractor():
    return HTTPExtractor(source_uri="https://example.com/data.csv")


@pytest.fixture
def templated_extractor():
    return HTTPExtractor(source_uri="https://example.com/{path}")


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

class TestHTTPExtractorModel:

    def test_source_uri_is_stored(self, extractor):
        assert extractor.source_uri == "https://example.com/data.csv"

    def test_source_uri_is_a_template_field(self):
        field = HTTPExtractor.model_fields["source_uri"]
        assert field.json_schema_extra.get("template") is True

    def test_source_uri_is_required(self):
        with pytest.raises(Exception):
            HTTPExtractor()  # noqa

    def test_templated_source_uri_accepted(self, templated_extractor):
        assert "{path}" in templated_extractor.source_uri


# ---------------------------------------------------------------------------
# HTTPExtractor.extract – successful responses
# ---------------------------------------------------------------------------

class TestHTTPExtractorSuccess:

    def test_returns_bytesio(self, extractor):
        response = _make_response(chunks=[b"hello"])
        with patch("requests.get", return_value=response):
            result = extractor.extract()
        assert isinstance(result, BytesIO)

    def test_returned_bytesio_is_seeked_to_zero(self, extractor):
        response = _make_response(chunks=[b"hello"])
        with patch("requests.get", return_value=response):
            result = extractor.extract()
        assert result.tell() == 0

    def test_content_is_written_to_bytesio(self, extractor):
        response = _make_response(chunks=[b"hello ", b"world"])
        with patch("requests.get", return_value=response):
            result = extractor.extract()
        assert result.read() == b"hello world"

    def test_multiple_chunks_are_concatenated(self, extractor):
        chunks = [b"chunk1", b"chunk2", b"chunk3"]
        response = _make_response(chunks=chunks)
        with patch("requests.get", return_value=response):
            result = extractor.extract()
        assert result.read() == b"chunk1chunk2chunk3"

    def test_empty_chunks_are_skipped(self, extractor):
        response = _make_response(chunks=[b"data", b"", b"more"])
        with patch("requests.get", return_value=response):
            result = extractor.extract()
        assert result.read() == b"datamore"

    def test_requests_get_called_with_correct_uri(self, extractor):
        response = _make_response(chunks=[b"data"])
        with patch("requests.get", return_value=response) as mock_get:
            extractor.extract()
        mock_get.assert_called_once_with("https://example.com/data.csv", timeout=120)

    def test_template_uri_is_rendered_before_request(self, templated_extractor):
        response = _make_response(chunks=[b"data"])
        with patch("requests.get", return_value=response) as mock_get:
            templated_extractor.extract(path="files/data.csv")
        mock_get.assert_called_once_with("https://example.com/files/data.csv", timeout=120)

    def test_timeout_is_120_seconds(self, extractor):
        response = _make_response(chunks=[b"data"])
        with patch("requests.get", return_value=response) as mock_get:
            extractor.extract()
        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 120

    def test_iter_content_called_with_chunk_size(self, extractor):
        response = _make_response(chunks=[b"data"])
        with patch("requests.get", return_value=response):
            extractor.extract()
        response.iter_content.assert_called_once_with(chunk_size=8192)


# ---------------------------------------------------------------------------
# HTTPExtractor.extract – error handling
# ---------------------------------------------------------------------------

class TestHTTPExtractorErrors:

    def test_timeout_raises_etl_error(self, extractor):
        with patch("requests.get", side_effect=requests.exceptions.Timeout()):
            with pytest.raises(ETLError, match="timed out"):
                extractor.extract()

    def test_timeout_error_includes_uri(self, extractor):
        with patch("requests.get", side_effect=requests.exceptions.Timeout()):
            with pytest.raises(ETLError, match="https://example.com/data.csv"):
                extractor.extract()

    def test_timeout_error_chains_original_exception(self, extractor):
        original = requests.exceptions.Timeout()
        with patch("requests.get", side_effect=original):
            with pytest.raises(ETLError) as exc_info:
                extractor.extract()
        assert exc_info.value.__cause__ is original

    def test_request_exception_raises_etl_error(self, extractor):
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("refused")):
            with pytest.raises(ETLError, match="Failed to connect"):
                extractor.extract()

    def test_request_exception_includes_uri(self, extractor):
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("refused")):
            with pytest.raises(ETLError, match="https://example.com/data.csv"):
                extractor.extract()

    def test_request_exception_chains_original_exception(self, extractor):
        original = requests.exceptions.ConnectionError("refused")
        with patch("requests.get", side_effect=original):
            with pytest.raises(ETLError) as exc_info:
                extractor.extract()
        assert exc_info.value.__cause__ is original

    @pytest.mark.parametrize("status_code", [401, 403])
    def test_auth_failure_raises_etl_error(self, extractor, status_code):
        response = _make_response(status_code=status_code)
        with patch("requests.get", return_value=response):
            with pytest.raises(ETLError, match="Failed to authenticate"):
                extractor.extract()

    @pytest.mark.parametrize("status_code", [401, 403])
    def test_auth_failure_includes_uri(self, extractor, status_code):
        response = _make_response(status_code=status_code)
        with patch("requests.get", return_value=response):
            with pytest.raises(ETLError, match="https://example.com/data.csv"):
                extractor.extract()

    def test_404_raises_etl_error(self, extractor):
        response = _make_response(status_code=404)
        with patch("requests.get", return_value=response):
            with pytest.raises(ETLError, match="could not be found"):
                extractor.extract()

    def test_404_includes_uri(self, extractor):
        response = _make_response(status_code=404)
        with patch("requests.get", return_value=response):
            with pytest.raises(ETLError, match="https://example.com/data.csv"):
                extractor.extract()

    @pytest.mark.parametrize("status_code", [400, 429, 500, 503])
    def test_generic_4xx_5xx_raises_etl_error(self, extractor, status_code):
        response = _make_response(status_code=status_code)
        with patch("requests.get", return_value=response):
            with pytest.raises(ETLError, match=str(status_code)):
                extractor.extract()

    @pytest.mark.parametrize("status_code", [400, 429, 500, 503])
    def test_generic_error_includes_uri(self, extractor, status_code):
        response = _make_response(status_code=status_code)
        with patch("requests.get", return_value=response):
            with pytest.raises(ETLError, match="https://example.com/data.csv"):
                extractor.extract()

    def test_empty_response_raises_etl_error(self, extractor):
        response = _make_response(status_code=200, chunks=[b"", b""])
        with patch("requests.get", return_value=response):
            with pytest.raises(ETLError, match="No data was returned"):
                extractor.extract()

    def test_empty_response_includes_uri(self, extractor):
        response = _make_response(status_code=200, chunks=[b"", b""])
        with patch("requests.get", return_value=response):
            with pytest.raises(ETLError, match="https://example.com/data.csv"):
                extractor.extract()

    def test_empty_iter_content_raises_etl_error(self, extractor):
        response = _make_response(status_code=200, chunks=[])
        with patch("requests.get", return_value=response):
            with pytest.raises(ETLError, match="No data was returned"):
                extractor.extract()

    @pytest.mark.parametrize("status_code", [200, 201, 206])
    def test_2xx_status_codes_do_not_raise(self, extractor, status_code):
        response = _make_response(status_code=status_code, chunks=[b"data"])
        with patch("requests.get", return_value=response):
            result = extractor.extract()
        assert isinstance(result, BytesIO)
