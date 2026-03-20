import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import get_ident
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from typing import Optional, Any
from io import BytesIO
from ..extractors import Extractor
from ..transformers import Transformer, ETLDataMapping
from ..loaders import Loader, ETLLoaderResult
from ..user_facing_errors import coerce_known_etl_error

logger = logging.getLogger(__name__)


class ETLStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    INCOMPLETE = "INCOMPLETE"


class ETLStage(Enum):
    SETUP = "SETUP"
    EXTRACT = "EXTRACT"
    TRANSFORM = "TRANSFORM"
    LOAD = "LOAD"


class ETLContext(BaseModel):
    status: ETLStatus = ETLStatus.PENDING
    stage: ETLStage = ETLStage.SETUP
    runtime_variables: dict[str, Any] = Field(default_factory=dict)
    log_entries: list[dict[str, Any]] = Field(default_factory=list)
    results: Optional[ETLLoaderResult] = None
    exception: Optional[Exception] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def mark_failed(self, exc: Exception) -> None:
        """
        Mark the ETL run as failed due to the given exception.
        """

        self.status = ETLStatus.FAILED
        self.exception = exc


def _record_timestamp(record: logging.LogRecord) -> str:
    return datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()


class _PipelineLogCaptureHandler(logging.Handler):
    def __init__(
        self,
        context: ETLContext,
        logger_names: set[str],
        thread_id: int,
    ):
        super().__init__(level=logging.DEBUG)
        self.context = context
        self.logger_names = logger_names
        self.thread_id = thread_id

    def emit(self, record: logging.LogRecord) -> None:
        if record.thread != self.thread_id:
            return

        if self.logger_names and not any(
            record.name == name or record.name.startswith(f"{name}.")
            for name in self.logger_names
        ):
            return

        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)

        self.context.log_entries.append(
            {
                "timestamp": _record_timestamp(record),
                "level": record.levelname,
                "message": message,
                "logger": record.name,
                "stage": self.context.stage.value,
            }
        )


class ETLPipeline(BaseModel):
    extractor: Extractor
    transformer: Transformer
    loader: Loader
    pre_extract_messages: list[dict[str, str]] = Field(default_factory=list)

    @staticmethod
    def _summarize_payload(payload: Any) -> dict[str, Any]:
        if isinstance(payload, BytesIO):
            current_position = payload.tell()
            payload.seek(0, 2)
            size = payload.tell()
            payload.seek(current_position)
            return {
                "type": "BytesIO",
                "bytes": size,
            }

        if hasattr(payload, "shape") and hasattr(payload, "columns"):
            rows, columns = payload.shape
            summary = {
                "type": type(payload).__name__,
                "rows": int(rows),
                "columns": int(columns) - (1 if "target_id" in payload.columns else 0),
            }
            if "target_id" in payload.columns:
                summary["datastreams"] = int(payload["target_id"].nunique())
            return summary

        return {
            "type": type(payload).__name__,
        }

    def _log_capture_names(self) -> set[str]:
        names = {
            __name__,
            self.extractor.__module__,
            self.transformer.__module__,
            self.loader.__module__,
        }

        if any(name.startswith("hydroserverpy.etl") for name in names):
            names.add("hydroserverpy.etl")

        return {name for name in names if name}

    @contextmanager
    def _capture_logs(self, context: ETLContext):
        logger_names = self._log_capture_names()
        root_logger = logging.getLogger()
        handler = _PipelineLogCaptureHandler(
            context=context,
            logger_names=logger_names,
            thread_id=get_ident(),
        )
        original_levels = {
            name: logging.getLogger(name).level
            for name in logger_names
        }

        for name in logger_names:
            logging.getLogger(name).setLevel(logging.INFO)

        root_logger.addHandler(handler)
        try:
            yield
        finally:
            root_logger.removeHandler(handler)
            for name, level in original_levels.items():
                logging.getLogger(name).setLevel(level)

    def run(
        self,
        data_mappings: list[ETLDataMapping],
        raise_on_error: bool = True,
        **kwargs
    ) -> ETLContext:
        """
        Execute the ETL pipeline across extract, transform, and load stages.

        If raise_on_error is True, the first exception raised by any stage
        will be propagated to the caller. If raise_on_error is False, the
        ETLContext will be marked as failed and returned.
        """

        context = ETLContext()

        with self._capture_logs(context):
            context.status = ETLStatus.RUNNING
            context.stage = ETLStage.EXTRACT

            try:
                context.runtime_variables["extractor"] = self.extractor.render_runtime_data(
                    **kwargs
                )
                context.runtime_variables["transformer"] = self.transformer.render_runtime_data(
                    **kwargs
                )
                context.runtime_variables["loader"] = self.loader.render_runtime_data(
                    **kwargs
                )
                extractor_runtime = context.runtime_variables.get("extractor") or {}
                source_uri = extractor_runtime.get("source_uri") or extractor_runtime.get("sourceUri")
            except Exception as e:
                coerced = coerce_known_etl_error(e)
                logger.error("%s", coerced)
                if raise_on_error:
                    if coerced is e:
                        raise
                    raise coerced from e
                context.mark_failed(coerced)
                return context

            try:
                logger.info("Starting extract")
                for entry in self.pre_extract_messages:
                    level_name = (entry.get("level") or "INFO").upper()
                    level = getattr(logging, level_name, logging.INFO)
                    logger.log(level, "%s", entry.get("message") or "")
                if source_uri:
                    logger.info("Resolved runtime source URI: %s", source_uri)
                extracted_payload = self.extractor.extract(**kwargs)
                logger.info(
                    "Extractor returned payload: %s",
                    self._summarize_payload(extracted_payload),
                )
            except Exception as e:
                coerced = coerce_known_etl_error(e)
                logger.error("Extract step failed: %s", coerced)
                if raise_on_error:
                    if coerced is e:
                        raise
                    raise coerced from e
                context.mark_failed(coerced)
                return context

            context.stage = ETLStage.TRANSFORM

            try:
                logger.info("Starting transform")
                transformed_payload = self.transformer.transform(
                    payload=extracted_payload,
                    data_mappings=data_mappings,
                    **kwargs
                )
                logger.info(
                    "Transform result: %s",
                    self._summarize_payload(transformed_payload),
                )
            except Exception as e:
                coerced = coerce_known_etl_error(e)
                logger.error("Transform step failed: %s", coerced)
                if raise_on_error:
                    if coerced is e:
                        raise
                    raise coerced from e
                context.mark_failed(coerced)
                return context

            context.stage = ETLStage.LOAD

            try:
                logger.info("Starting load")
                context.results = self.loader.load(
                    payload=transformed_payload,
                    **kwargs
                )
            except Exception as e:
                coerced = coerce_known_etl_error(e)
                logger.error("Load step failed: %s", coerced)
                if raise_on_error:
                    if coerced is e:
                        raise
                    raise coerced from e
                context.mark_failed(coerced)
                return context

            if context.results.failure_count == 0:
                context.status = ETLStatus.SUCCESS
            else:
                context.status = ETLStatus.INCOMPLETE

        return context
