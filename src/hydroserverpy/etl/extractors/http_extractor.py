import logging
import requests
from io import BytesIO

from ..etl_configuration import Task
from .base import Extractor, ExtractorConfig


logger = logging.getLogger(__name__)


class HTTPExtractor(Extractor):
    def __init__(self, settings: ExtractorConfig):
        super().__init__(settings)

    def extract(self, task: Task, loader=None):
        """
        Downloads the file from the HTTP/HTTPS server and returns a file-like object.
        """
        url = self.resolve_placeholder_variables(task, loader)
        logger.info("Requesting data from source URI")

        try:
            response = requests.get(url)
        except requests.exceptions.Timeout as e:
            raise ValueError(
                "The source system did not respond before the timeout."
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise ValueError("Could not connect to the source system.") from e
        except requests.exceptions.RequestException as e:
            # Generic network/client error.
            raise ValueError("Could not connect to the source system.") from e

        status = getattr(response, "status_code", None)
        if status in (401, 403):
            raise ValueError(
                "Authentication with the source system failed. The username, password, or token may be incorrect or expired."
            )
        if status == 404:
            raise ValueError(
                "The requested data could not be found on the source system."
            )
        if status is not None and status >= 400:
            logger.error(
                "HTTP request failed (status=%s) for %s",
                status,
                url,
            )
            raise ValueError("The source system returned an error.")

        data = BytesIO()
        total_bytes = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                total_bytes += len(chunk)
                data.write(chunk)
        data.seek(0)

        if total_bytes == 0:
            raise ValueError(
                "The connection to the source worked but no observations were returned."
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
