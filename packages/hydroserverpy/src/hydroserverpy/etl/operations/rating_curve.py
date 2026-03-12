import logging
import numpy as np
import pandas as pd
import requests
from functools import lru_cache
from io import BytesIO
from urllib.parse import unquote, urlparse
from .base import DataOperation
from ..exceptions import ETLError


logger = logging.getLogger(__name__)


def fetch_remote_rating_curve_file(rating_curve_uri: str) -> bytes:
    """
    Retrieve a rating curve file from a local or remote URI.

    The URI must use one of the supported schemes: http, https, or file.
    For HTTP(S) URIs, the file is retrieved via an HTTP GET request.
    For file URIs, the file is read from the local filesystem.
    """

    parsed_uri = urlparse(rating_curve_uri)
    scheme = parsed_uri.scheme.lower()

    if scheme in {"http", "https"}:
        timeout_seconds = 30
        try:
            response = requests.get(rating_curve_uri, timeout=timeout_seconds)
        except requests.exceptions.Timeout as e:
            raise ETLError(
                f"Request to retrieve rating curve file at {rating_curve_uri} "
                f"timed out after {timeout_seconds} seconds."
            ) from e
        except requests.exceptions.RequestException as e:
            raise ETLError(
                f"Failed to retrieve rating curve file at {rating_curve_uri}"
            ) from e

        if response.status_code == 404:
            raise ETLError(
                f"Rating curve file not found at {rating_curve_uri}"
            )
        if response.status_code in (401, 403):
            raise ETLError(
                f"Authentication failed while retrieving rating curve file at {rating_curve_uri}"
            )
        if response.status_code >= 400:
            raise ETLError(
                f"Rating curve request to {rating_curve_uri} "
                f"failed with HTTP status code {response.status_code}"
            )

        payload = response.content

    elif scheme == "file":
        netloc = parsed_uri.netloc or ""
        path = unquote(parsed_uri.path or "")

        if netloc:
            path = f"//{netloc}{path}"

        try:
            with open(path, "rb") as file_obj:
                payload = file_obj.read()
        except FileNotFoundError as e:
            raise ETLError(
                f"Rating curve file not found at {rating_curve_uri}"
            ) from e
        except OSError as e:
            raise ETLError(
                f"Failed to read rating curve file at {rating_curve_uri}"
            ) from e

    else:
        raise ETLError(
            f"Unsupported rating file scheme {scheme} at {rating_curve_uri}. "
            f"Must be one of: http, https, file"
        )

    if not payload:
        raise ETLError(
            f"Rating curve at {rating_curve_uri} is empty."
        )

    return payload


@lru_cache(maxsize=128)
def load_rating_curve(rating_curve_uri: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Load and parse a rating curve CSV file into numeric lookup arrays.

    The rating curve file is retrieved from the provided URI, parsed as CSV,
    and standardized to two numeric columns representing input and output
    values. Rows with non-numeric values are dropped. The resulting input
    values are sorted in ascending order, and duplicate input values are
    resolved by keeping the last occurrence.

    Results are cached by URI to avoid repeated retrieval and parsing of the
    same rating curve.
    """

    rating_curve_payload = fetch_remote_rating_curve_file(rating_curve_uri)

    try:
        lookup_df = pd.read_csv(BytesIO(rating_curve_payload))
    except Exception as e:
        raise ETLError(
            f"Rating curve at {rating_curve_uri} is not a valid CSV file."
        ) from e

    if lookup_df.shape[1] < 2:
        raise ETLError(
            f"Rating curve at {rating_curve_uri} must contain at least two columns "
            f"(input and output)."
        )

    standardized = lookup_df.iloc[:, :2].copy()
    standardized.columns = ["input_value", "output_value"]
    standardized["input_value"] = pd.to_numeric(
        standardized["input_value"], errors="coerce"
    )
    standardized["output_value"] = pd.to_numeric(
        standardized["output_value"], errors="coerce"
    )
    standardized = (
        standardized.dropna(subset=["input_value", "output_value"])
        .sort_values("input_value")
        .drop_duplicates(subset=["input_value"], keep="last")
    )

    if standardized.empty or len(standardized.index) < 2:
        raise ETLError(
            f"Rating curve at {rating_curve_uri} must include at least two numeric rows."
        )

    return (
        standardized["input_value"].to_numpy(dtype=np.float64),
        standardized["output_value"].to_numpy(dtype=np.float64),
    )


class RatingCurveDataOperation(DataOperation):
    rating_curve_url: str

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply a rating curve transformation to the value column of a
        (timestamp, value) DataFrame.

        The rating curve is loaded from the provided URL and used to map numeric
        values to output values using linear interpolation. Non-numeric values
        are coerced to NaN and remain NaN in the output. Values outside the range
        of the rating curve are clamped to the nearest endpoint of the curve.
        The timestamp column is passed through unchanged.
        """

        lookup_input, lookup_output = load_rating_curve(self.rating_curve_url)

        series_numeric = pd.to_numeric(df["value"], errors="coerce")
        series_values = series_numeric.to_numpy(dtype=np.float64)
        finite_mask = np.isfinite(series_values)

        transformed_values = np.full(series_values.shape, np.nan, dtype=np.float64)

        if finite_mask.any():
            transformed_values[finite_mask] = np.interp(
                series_values[finite_mask],
                lookup_input,
                lookup_output,
                left=lookup_output[0],
                right=lookup_output[-1],
            )

        logger.debug(
            "Applied rating curve transformation for target=%r using reference=%r.",
            self.target_identifier,
            self.rating_curve_url,
        )

        result = df.copy()
        result["value"] = pd.Series(transformed_values, index=df.index, dtype="float64")
        return result
