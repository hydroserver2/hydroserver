import logging
from .base import Extractor
from ..etl_configuration import ExtractorConfig


logger = logging.getLogger(__name__)


class LocalFileExtractor(Extractor):
    def __init__(self, extractor_config: ExtractorConfig):
        super().__init__(extractor_config)

    def extract(self, task=None, loader=None):
        """
        Opens the file and returns a file-like object.
        """
        path = (
            self.resolve_placeholder_variables(task, loader)
            if task is not None
            else self.cfg.source_uri
        )
        try:
            file_handle = open(path, "r")
            logger.debug("Successfully opened local file %r.", path)
            return file_handle
        except FileNotFoundError as e:
            raise ValueError("This job references a resource that no longer exists.") from e
        except Exception as e:
            logger.error("Error opening local file %r: %s", path, e, exc_info=True)
            raise ValueError("Could not open the source file.") from e
