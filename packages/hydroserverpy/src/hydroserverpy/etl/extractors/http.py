import logging
import requests
from io import BytesIO
from typing import Union, TextIO
from pydantic import Field
from .base import Extractor
from ..exceptions import ETLError


logger = logging.getLogger(__name__)


class HTTPExtractor(Extractor):
    source_uri: str = Field(..., json_schema_extra={"template": True})

    def extract(
        self,
        **kwargs
    ) -> Union[str, TextIO, BytesIO]:
        """
        Downloads a file from an HTTP/HTTPS server and returns a file-like object.
        """

        runtime_data = self.render_runtime_data(**kwargs)
        source_uri = runtime_data['source_uri']

        timeout_seconds = 120
        logger.info(f"Requesting data from {source_uri}")

        try:
            response = requests.get(source_uri, timeout=timeout_seconds)
        except requests.exceptions.Timeout as e:
            raise ETLError(
                f"Request to {source_uri} timed out after {timeout_seconds} seconds."
                "The server may be busy or unreachable. "
                "Check the server status, then try again."
            ) from e
        except requests.exceptions.RequestException as e:
            raise ETLError(
                f"Failed to connect to {source_uri} with error: {str(e)} "
            ) from e

        status_code = getattr(response, "status_code", None)

        if status_code in (401, 403):
            raise ETLError(
                f"Failed to authenticate with {source_uri}. "
                f"The username, password, or token may be incorrect or expired."
            )
        if status_code == 404:
            raise ETLError(
                f"The requested data could not be found at {source_uri}. "
                "This may indicate that the resource does not exist, has been moved, or the URL is incorrect. "
                "Verify the URL and the availability of the resource, then try again."
            )
        if status_code is not None and status_code >= 400:
            raise ETLError(
                f"HTTP request failed with status code {status_code} for {source_uri}. "
                "This may indicate a client or server error. "
                "Check that the URL is correct, the server is reachable, "
                "and any required authentication or permissions are valid."
            )

        data = BytesIO()
        total_bytes = 0

        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                total_bytes += len(chunk)
                data.write(chunk)

        data.seek(0)

        if total_bytes == 0:
            raise ETLError(
                f"No data was returned from {source_uri}. "
                "The server may be temporarily unavailable, the resource could be empty, "
                "or the request parameters may not match any available data. "
                "Verify the URL, check the server status, and ensure your request is correct."
            )

        # Keep payload-level details at DEBUG; hydroserver-api-services already logs
        # a concise "Extractor returned payload" line for the end user.
        logger.debug(
            "Extractor returned payload (status=%s, content_type=%r, bytes=%s).",
            getattr(response, "status_code", None),
            (
                response.headers.get("Content-Type")
                if hasattr(response, "headers")
                else None
            ),
            total_bytes,
        )

        return data
