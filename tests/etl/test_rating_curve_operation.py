import pytest
import numpy as np
import pandas as pd
import requests
from unittest.mock import patch, MagicMock

from hydroserverpy.etl.operations.rating_curve import (
    RatingCurveDataOperation,
    fetch_remote_rating_curve_file,
    load_rating_curve,
)
from hydroserverpy.etl.exceptions import ETLError


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

SIMPLE_CURVE_CSV = b"input,output\n0,0\n10,100\n20,200\n"
SIMPLE_CURVE_URL = "https://example.com/curve.csv"


def _make_op(url=SIMPLE_CURVE_URL, target_identifier="target_1"):
    return RatingCurveDataOperation(
        type="rating_curve",
        rating_curve_url=url,
        target_identifier=target_identifier,
    )


def _make_http_response(status_code=200, content=SIMPLE_CURVE_CSV):
    response = MagicMock()
    response.status_code = status_code
    response.content = content
    return response


def _make_tv_df(*values):
    """Build a (timestamp, value) DataFrame with UTC timestamps."""
    timestamps = pd.date_range("2024-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.DataFrame({"timestamp": timestamps, "value": list(values)}, dtype=object).assign(
        timestamp=lambda df: pd.to_datetime(df["timestamp"]),
        value=lambda df: pd.to_numeric(df["value"], errors="coerce"),
    )


def _patch_fetch(content=SIMPLE_CURVE_CSV):
    """Patch fetch_remote_rating_curve_file to return the given bytes."""
    return patch(
        "hydroserverpy.etl.operations.rating_curve.fetch_remote_rating_curve_file",
        return_value=content,
    )


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

class TestRatingCurveDataOperationModel:

    def test_rating_curve_url_is_stored(self):
        op = _make_op()
        assert op.rating_curve_url == SIMPLE_CURVE_URL

    def test_target_identifier_is_stored(self):
        op = _make_op(target_identifier="my_target")
        assert op.target_identifier == "my_target"

    def test_rating_curve_url_is_required(self):
        with pytest.raises(Exception):
            RatingCurveDataOperation(type="rating_curve", target_identifier="t")  # noqa

    def test_target_identifier_is_required(self):
        with pytest.raises(Exception):
            RatingCurveDataOperation(type="rating_curve", rating_curve_url=SIMPLE_CURVE_URL)  # noqa


# ---------------------------------------------------------------------------
# fetch_remote_rating_curve_file – HTTP
# ---------------------------------------------------------------------------

class TestFetchRemoteRatingCurveFileHTTP:

    def test_returns_content_for_200_response(self):
        with patch("requests.get", return_value=_make_http_response(200, b"data")):
            result = fetch_remote_rating_curve_file(SIMPLE_CURVE_URL)
        assert result == b"data"

    def test_timeout_raises_etl_error(self):
        with patch("requests.get", side_effect=requests.exceptions.Timeout()):
            with pytest.raises(ETLError, match="timed out"):
                fetch_remote_rating_curve_file(SIMPLE_CURVE_URL)

    def test_timeout_error_includes_uri(self):
        with patch("requests.get", side_effect=requests.exceptions.Timeout()):
            with pytest.raises(ETLError, match=SIMPLE_CURVE_URL):
                fetch_remote_rating_curve_file(SIMPLE_CURVE_URL)

    def test_timeout_chains_original_exception(self):
        original = requests.exceptions.Timeout()
        with patch("requests.get", side_effect=original):
            with pytest.raises(ETLError) as exc_info:
                fetch_remote_rating_curve_file(SIMPLE_CURVE_URL)
        assert exc_info.value.__cause__ is original

    def test_request_exception_raises_etl_error(self):
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError()):
            with pytest.raises(ETLError, match="Failed to retrieve"):
                fetch_remote_rating_curve_file(SIMPLE_CURVE_URL)

    def test_404_raises_etl_error(self):
        with patch("requests.get", return_value=_make_http_response(404)):
            with pytest.raises(ETLError, match="not found"):
                fetch_remote_rating_curve_file(SIMPLE_CURVE_URL)

    @pytest.mark.parametrize("status_code", [401, 403])
    def test_auth_failure_raises_etl_error(self, status_code):
        with patch("requests.get", return_value=_make_http_response(status_code)):
            with pytest.raises(ETLError, match="Authentication failed"):
                fetch_remote_rating_curve_file(SIMPLE_CURVE_URL)

    @pytest.mark.parametrize("status_code", [400, 500, 503])
    def test_generic_error_status_raises_etl_error(self, status_code):
        with patch("requests.get", return_value=_make_http_response(status_code)):
            with pytest.raises(ETLError, match=str(status_code)):
                fetch_remote_rating_curve_file(SIMPLE_CURVE_URL)

    def test_empty_content_raises_etl_error(self):
        with patch("requests.get", return_value=_make_http_response(200, b"")):
            with pytest.raises(ETLError, match="empty"):
                fetch_remote_rating_curve_file(SIMPLE_CURVE_URL)


# ---------------------------------------------------------------------------
# fetch_remote_rating_curve_file – file://
# ---------------------------------------------------------------------------

class TestFetchRemoteRatingCurveFileLocal:

    def test_returns_file_content(self, tmp_path):
        curve_file = tmp_path / "curve.csv"
        curve_file.write_bytes(b"input,output\n0,0\n10,100\n")
        uri = curve_file.as_uri()
        result = fetch_remote_rating_curve_file(uri)
        assert result == b"input,output\n0,0\n10,100\n"

    def test_missing_file_raises_etl_error(self, tmp_path):
        uri = (tmp_path / "nonexistent.csv").as_uri()
        with pytest.raises(ETLError, match="not found"):
            fetch_remote_rating_curve_file(uri)

    def test_missing_file_chains_file_not_found_error(self, tmp_path):
        uri = (tmp_path / "nonexistent.csv").as_uri()
        with pytest.raises(ETLError) as exc_info:
            fetch_remote_rating_curve_file(uri)
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    def test_empty_file_raises_etl_error(self, tmp_path):
        curve_file = tmp_path / "empty.csv"
        curve_file.write_bytes(b"")
        uri = curve_file.as_uri()
        with pytest.raises(ETLError, match="empty"):
            fetch_remote_rating_curve_file(uri)

    def test_unsupported_scheme_raises_etl_error(self):
        with pytest.raises(ETLError, match="Unsupported"):
            fetch_remote_rating_curve_file("ftp://example.com/curve.csv")

    def test_unsupported_scheme_error_includes_scheme(self):
        with pytest.raises(ETLError, match="ftp"):
            fetch_remote_rating_curve_file("ftp://example.com/curve.csv")


# ---------------------------------------------------------------------------
# load_rating_curve
# ---------------------------------------------------------------------------

class TestLoadRatingCurve:

    def test_returns_two_numpy_arrays(self):
        with _patch_fetch():
            result = load_rating_curve.__wrapped__(SIMPLE_CURVE_URL)
        assert len(result) == 2
        assert isinstance(result[0], np.ndarray)
        assert isinstance(result[1], np.ndarray)

    def test_input_array_values(self):
        with _patch_fetch():
            inputs, _ = load_rating_curve.__wrapped__(SIMPLE_CURVE_URL)
        np.testing.assert_array_equal(inputs, [0.0, 10.0, 20.0])

    def test_output_array_values(self):
        with _patch_fetch():
            _, outputs = load_rating_curve.__wrapped__(SIMPLE_CURVE_URL)
        np.testing.assert_array_equal(outputs, [0.0, 100.0, 200.0])

    def test_input_values_are_sorted_ascending(self):
        csv = b"input,output\n20,200\n0,0\n10,100\n"
        with _patch_fetch(csv):
            inputs, _ = load_rating_curve.__wrapped__(SIMPLE_CURVE_URL)
        assert list(inputs) == sorted(inputs)

    def test_duplicate_input_keeps_last(self):
        csv = b"input,output\n10,100\n10,999\n20,200\n"
        with _patch_fetch(csv):
            inputs, outputs = load_rating_curve.__wrapped__(SIMPLE_CURVE_URL)
        idx = list(inputs).index(10.0)
        assert outputs[idx] == 999.0

    def test_non_numeric_rows_are_dropped(self):
        csv = b"input,output\n0,0\nbad,row\n10,100\n"
        with _patch_fetch(csv):
            inputs, _ = load_rating_curve.__wrapped__(SIMPLE_CURVE_URL)
        assert len(inputs) == 2

    def test_invalid_csv_raises_etl_error(self):
        with _patch_fetch(b"\x00\x01\x02"):
            with pytest.raises(ETLError, match="at least two columns"):
                load_rating_curve.__wrapped__(SIMPLE_CURVE_URL)

    def test_single_column_raises_etl_error(self):
        csv = b"input\n0\n10\n20\n"
        with _patch_fetch(csv):
            with pytest.raises(ETLError, match="at least two columns"):
                load_rating_curve.__wrapped__(SIMPLE_CURVE_URL)

    def test_fewer_than_two_numeric_rows_raises_etl_error(self):
        csv = b"input,output\n0,0\n"
        with _patch_fetch(csv):
            with pytest.raises(ETLError, match="at least two numeric rows"):
                load_rating_curve.__wrapped__(SIMPLE_CURVE_URL)

    def test_all_non_numeric_rows_raises_etl_error(self):
        csv = b"input,output\nbad,row\nalso,bad\n"
        with _patch_fetch(csv):
            with pytest.raises(ETLError, match="at least two numeric rows"):
                load_rating_curve.__wrapped__(SIMPLE_CURVE_URL)

    def test_only_first_two_columns_are_used(self):
        csv = b"input,output,extra\n0,0,ignored\n10,100,ignored\n"
        with _patch_fetch(csv):
            inputs, outputs = load_rating_curve.__wrapped__(SIMPLE_CURVE_URL)
        assert len(inputs) == 2


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

class TestRatingCurveDataOperationApply:

    def test_returns_dataframe(self):
        with _patch_fetch():
            result = _make_op().apply(_make_tv_df(5.0))
        assert isinstance(result, pd.DataFrame)

    def test_result_has_timestamp_and_value_columns(self):
        with _patch_fetch():
            result = _make_op().apply(_make_tv_df(5.0))
        assert "timestamp" in result.columns
        assert "value" in result.columns

    def test_timestamp_column_is_unchanged(self):
        with _patch_fetch():
            df = _make_tv_df(5.0, 15.0)
            result = _make_op().apply(df)
        pd.testing.assert_series_equal(result["timestamp"], df["timestamp"])

    def test_interpolates_midpoint(self):
        with _patch_fetch():
            result = _make_op().apply(_make_tv_df(5.0))
        assert result["value"].iloc[0] == pytest.approx(50.0)

    def test_exact_input_value(self):
        with _patch_fetch():
            result = _make_op().apply(_make_tv_df(10.0))
        assert result["value"].iloc[0] == pytest.approx(100.0)

    def test_value_below_range_is_clamped_to_left(self):
        with _patch_fetch():
            result = _make_op().apply(_make_tv_df(-999.0))
        assert result["value"].iloc[0] == pytest.approx(0.0)

    def test_value_above_range_is_clamped_to_right(self):
        with _patch_fetch():
            result = _make_op().apply(_make_tv_df(999.0))
        assert result["value"].iloc[0] == pytest.approx(200.0)

    def test_nan_input_produces_nan_output(self):
        with _patch_fetch():
            result = _make_op().apply(_make_tv_df(float("nan")))
        assert np.isnan(result["value"].iloc[0])

    def test_non_numeric_input_produces_nan_output(self):
        with _patch_fetch():
            timestamps = pd.date_range("2024-01-01", periods=1, freq="D", tz="UTC")
            df = pd.DataFrame({"timestamp": timestamps, "value": ["not a number"]})
            result = _make_op().apply(df)
        assert np.isnan(result["value"].iloc[0])

    def test_preserves_index(self):
        with _patch_fetch():
            timestamps = pd.to_datetime(["2024-01-01", "2024-01-02"], utc=True)
            df = pd.DataFrame({"timestamp": timestamps, "value": [5.0, 15.0]}, index=[10, 20])
            result = _make_op().apply(df)
        assert list(result.index) == [10, 20]

    def test_mixed_valid_and_nan_input(self):
        with _patch_fetch():
            result = _make_op().apply(_make_tv_df(5.0, float("nan"), 15.0))
        assert result["value"].iloc[0] == pytest.approx(50.0)
        assert np.isnan(result["value"].iloc[1])
        assert result["value"].iloc[2] == pytest.approx(150.0)

    def test_output_dtype_is_float64(self):
        with _patch_fetch():
            result = _make_op().apply(_make_tv_df(5.0))
        assert result["value"].dtype == np.float64
