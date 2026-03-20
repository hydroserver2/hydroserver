import logging
from io import BytesIO
from typing import Union, TextIO
from pydantic import Field
from .base import Extractor
from ..exceptions import ETLError


logger = logging.getLogger(__name__)


class LocalFileExtractor(Extractor):
    source_uri: str = Field(..., json_schema_extra={"template": True})

    def extract(
        self,
        **kwargs
    ) -> Union[str, TextIO, BytesIO]:
        """
        Opens a locally available file and returns a text-mode file handle seeked to the
        beginning of the file. The caller is responsible for closing the handle after use.
        """

        runtime_data = self.render_runtime_data(**kwargs)
        source_uri = runtime_data['source_uri']

        logger.info(f"Opening local data file {source_uri}")

        try:
            file_handle = open(source_uri, "r")
        except FileNotFoundError as e:
            raise ETLError(
                f"Local data file {source_uri} not found. "
                "Ensure the file exists at the specified path, "
                "and verify that the extractor has access to the directory."
            ) from e
        except Exception as e:
            raise ETLError(
                f"Failed to open local data file {source_uri}. "
                "This could be due to permission issues, a locked file, or an invalid path. "
                "Verify the file path and access rights."
            ) from e

        is_empty = file_handle.read(1) == ""
        file_handle.seek(0)

        if is_empty:
            file_handle.close()
            raise ETLError(
                f"Local data file {source_uri} is empty (0 bytes). "
                "Ensure the source file contains data and is not truncated."
            )

        logger.debug(
            "Successfully opened local file %r for data extract.",
            source_uri
        )

        return file_handle
