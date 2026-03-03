import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone as dt_timezone
import os
from typing import Any, Optional
from uuid import UUID
import pandas as pd
from celery import shared_task
from pydantic import TypeAdapter, ValidationError
from celery.signals import task_prerun, task_success, task_failure, task_postrun
from django.utils import timezone
from django.db.utils import IntegrityError
from django.core.management import call_command
from domains.etl.models import Task, TaskRun
from .loader import HydroServerInternalLoader, LoadSummary
from .etl_errors import (
    EtlUserFacingError,
    user_facing_error_from_exception,
    user_facing_error_from_validation_error,
)
from .run_result_normalizer import normalize_task_run_result, task_transformer_raw
from hydroserverpy.etl.factories import extractor_factory, transformer_factory
from hydroserverpy.etl.etl_configuration import (
    ExtractorConfig,
    TransformerConfig,
    SourceTargetMapping,
    MappingPath,
)


@dataclass
class TaskRunContext:
    stage: str = "setup"
    runtime_source_uri: Optional[str] = None
    log_handler: Optional["TaskLogHandler"] = None
    task_meta: dict[str, Any] = field(default_factory=dict)


class TaskLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        path = (record.pathname or "").replace("\\", "/")
        return "/hydroserverpy/" in path or "/domains/etl/" in path


class TaskLogHandler(logging.Handler):
    def __init__(self, context: TaskRunContext):
        super().__init__(level=logging.INFO)
        self.context = context
        self.lines: list[str] = []
        self.entries: list[dict[str, Any]] = []
        self._formatter = logging.Formatter()

    def emit(self, record: logging.LogRecord) -> None:
        if not self.filter(record):
            return

        message = record.getMessage()

        timestamp = datetime.fromtimestamp(
            record.created, tz=dt_timezone.utc
        ).isoformat()
        line = f"{timestamp} {record.levelname:<8} {message}"
        if record.exc_info:
            line = f"{line}\n{self._formatter.formatException(record.exc_info)}"
        self.lines.append(line)

        entry: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "pathname": record.pathname,
            "lineno": record.lineno,
        }
        if record.exc_info:
            entry["exception"] = self._formatter.formatException(record.exc_info)
        self.entries.append(entry)

        self._capture_runtime_uri(message)

    def _capture_runtime_uri(self, message: str) -> None:
        if self.context.runtime_source_uri:
            return
        if "Resolved runtime source URI:" in message:
            self.context.runtime_source_uri = message.split(
                "Resolved runtime source URI:", 1
            )[1].strip()
            return
        if "Requesting data from" in message:
            if "→" in message:
                self.context.runtime_source_uri = message.split("→", 1)[1].strip()
                return
            if "from" in message:
                self.context.runtime_source_uri = message.split("from", 1)[1].strip()

    def as_text(self) -> str:
        return "\n".join(self.lines).strip()


TASK_RUN_CONTEXT: dict[str, TaskRunContext] = {}


@contextmanager
def capture_task_logs(context: TaskRunContext):
    logger = logging.getLogger()
    handler = TaskLogHandler(context)
    handler.addFilter(TaskLogFilter())
    context.log_handler = handler

    previous_level = logger.level
    if previous_level > logging.INFO:
        logger.setLevel(logging.INFO)

    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        if previous_level > logging.INFO:
            logger.setLevel(previous_level)


def _is_empty(data: Any) -> bool:
    if data is None:
        return True
    if isinstance(data, pd.DataFrame) and data.empty:
        return True
    return False


def _describe_payload(data: Any) -> dict[str, Any]:
    if isinstance(data, pd.DataFrame):
        return {
            "type": "DataFrame",
            "rows": len(data),
            "columns": len(data.columns),
        }
    info: dict[str, Any] = {"type": type(data).__name__}
    if isinstance(data, (bytes, bytearray)):
        info["bytes"] = len(data)
        return info
    # BytesIO and similar
    try:
        buf = getattr(data, "getbuffer", None)
        if callable(buf):
            info["bytes"] = len(data.getbuffer())
            return info
    except Exception:
        pass
    # Real file handles
    try:
        fileno = getattr(data, "fileno", None)
        if callable(fileno):
            info["bytes"] = os.fstat(data.fileno()).st_size
            return info
    except Exception:
        pass
    return info


def _describe_transformed_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, pd.DataFrame):
        return {"type": type(data).__name__}
    datastreams = [col for col in data.columns if col != "timestamp"]
    return {
        "type": "DataFrame",
        "rows": len(data),
        "columns": len(data.columns),
        "datastreams": len(datastreams),
    }


def _success_message(load: Optional[LoadSummary]) -> str:
    if not load:
        return "Load complete."

    loaded = load.observations_loaded
    if loaded == 0:
        if load.timestamps_total and load.timestamps_after_cutoff == 0:
            return "Already up to date. No new observations were loaded."
        # Otherwise, we don't have strong evidence for why nothing loaded beyond "no new observations".
        return "No new observations were loaded."

    ds_count = load.datastreams_loaded or 0
    preposition = "into" if ds_count == 1 else "across"
    ds_word = "datastream" if ds_count == 1 else "datastreams"
    return f"Loaded {loaded} total observations {preposition} {ds_count} {ds_word}."


def _apply_runtime_uri_aliases(result: dict[str, Any], runtime_source_uri: str) -> None:
    result.setdefault("runtime_source_uri", runtime_source_uri)
    result.setdefault("runtimeSourceUri", runtime_source_uri)
    result.setdefault("runtime_url", runtime_source_uri)
    result.setdefault("runtimeUrl", runtime_source_uri)


def _apply_log_aliases(result: dict[str, Any]) -> None:
    if "log_entries" in result and "logEntries" not in result:
        result["logEntries"] = result["log_entries"]


def _merge_result_with_context(
    result: dict[str, Any], context: Optional[TaskRunContext]
) -> dict[str, Any]:
    if "summary" not in result and "message" in result:
        result["summary"] = result["message"]

    if context:
        if context.runtime_source_uri and not (
            result.get("runtime_source_uri")
            or result.get("runtimeSourceUri")
            or result.get("runtime_url")
            or result.get("runtimeUrl")
        ):
            _apply_runtime_uri_aliases(result, context.runtime_source_uri)

        if context.log_handler:
            if "logs" not in result:
                logs_text = context.log_handler.as_text()
                if logs_text:
                    result["logs"] = logs_text
            if "log_entries" not in result and context.log_handler.entries:
                result["log_entries"] = context.log_handler.entries

    _apply_log_aliases(result)
    return result


def _build_task_result(
    message: str,
    context: Optional[TaskRunContext] = None,
    *,
    stage: Optional[str] = None,
    traceback: Optional[str] = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"message": message, "summary": message}
    if stage:
        result["stage"] = stage
    if traceback:
        result["traceback"] = traceback

    if context and context.runtime_source_uri:
        _apply_runtime_uri_aliases(result, context.runtime_source_uri)

    if context and context.task_meta and "task" not in result:
        result["task"] = context.task_meta

    if context and context.log_handler:
        logs_text = context.log_handler.as_text()
        if logs_text:
            result["logs"] = logs_text
        if context.log_handler.entries:
            result["log_entries"] = context.log_handler.entries

    _apply_log_aliases(result)
    return result


def _last_logged_error(context: Optional[TaskRunContext]) -> Optional[str]:
    if not context or not context.log_handler or not context.log_handler.entries:
        return None
    for entry in reversed(context.log_handler.entries):
        if entry.get("level") == "ERROR":
            msg = entry.get("message")
            if msg:
                return msg
    return None


def _mapped_csv_error_from_log(last_err: str) -> Optional[str]:
    prefix = "Error reading CSV data:"
    if not last_err.startswith(prefix):
        return None

    detail = last_err[len(prefix) :].strip()
    if detail == "One or more configured CSV columns were not found in the header row.":
        return (
            "Configured CSV columns were not found in the file header. "
            "This often means the delimiter or headerRow setting is incorrect. "
            "Verify the delimiter and headerRow settings, then run the job again."
        )
    if (
        detail
        == "The header row contained unexpected values and could not be processed."
    ):
        return (
            "A required column was not found in the file header. "
            "The source file may have changed or the header row may be set incorrectly. "
            "Confirm the file layout and update the column mappings if needed."
        )
    if (
        detail
        == "One or more data rows contained unexpected values and could not be processed."
    ):
        return (
            "A required column was not found in the file header. "
            "The source file may have changed or the header row may be set incorrectly. "
            "Confirm the file layout and update the column mappings if needed."
        )
    return None


def _validate_component_config(
    component: str, adapter: TypeAdapter, raw: dict[str, Any]
):
    try:
        return adapter.validate_python(raw)
    except ValidationError as ve:
        raise user_facing_error_from_validation_error(component, ve, raw=raw) from ve


@shared_task(bind=True, expires=10, name="etl.tasks.run_etl_task")
def run_etl_task(self, task_id: str):
    """
    Runs a HydroServer ETL task based on the task configuration provided.
    """

    task_run_id = self.request.id
    context = TaskRunContext()
    TASK_RUN_CONTEXT[task_run_id] = context

    with capture_task_logs(context):
        try:
            task = (
                Task.objects.select_related("data_connection")
                .prefetch_related("mappings", "mappings__paths")
                .get(pk=UUID(task_id))
            )

            context.task_meta = {
                "id": str(task.id),
                "name": task.name,
                "data_connection_id": str(task.data_connection_id),
                "data_connection_name": task.data_connection.name,
            }

            context.stage = "setup"
            extractor_raw = {
                "type": task.data_connection.extractor_type,
                **(task.data_connection.extractor_settings or {}),
            }
            transformer_raw = {
                "type": task.data_connection.transformer_type,
                **(task.data_connection.transformer_settings or {}),
            }

            timestamp_cfg = transformer_raw.get("timestamp") or {}
            if isinstance(timestamp_cfg, dict):
                tz_mode = timestamp_cfg.get("timezoneMode")
                tz_value = timestamp_cfg.get("timezone")
                if tz_mode == "daylightSavings" and not tz_value:
                    raise EtlUserFacingError(
                        "Timezone information is required when daylight savings mode is enabled. "
                        "Select a valid timezone such as America/Denver and try again."
                    )

            extractor_cfg = _validate_component_config(
                "extractor", TypeAdapter(ExtractorConfig), extractor_raw
            )
            transformer_cfg = _validate_component_config(
                "transformer", TypeAdapter(TransformerConfig), transformer_raw
            )

            extractor_cls = extractor_factory(extractor_cfg)
            transformer_cls = transformer_factory(transformer_cfg)
            loader_cls = HydroServerInternalLoader(task)

            task_mappings = [
                SourceTargetMapping(
                    source_identifier=task_mapping.source_identifier,
                    paths=[
                        MappingPath(
                            target_identifier=task_mapping_path.target_identifier,
                            data_transformations=task_mapping_path.data_transformations,
                        )
                        for task_mapping_path in task_mapping.paths.all()
                    ],
                )
                for task_mapping in task.mappings.all()
            ]

            context.stage = "extract"
            logging.info("Starting extract")
            data = extractor_cls.extract(task, loader_cls)
            context.runtime_source_uri = (
                getattr(extractor_cls, "runtime_source_uri", None)
                or context.runtime_source_uri
            )
            extract_summary = _describe_payload(data)
            logging.info("Extractor returned payload: %s", extract_summary)
            if _is_empty(data):
                if task.data_connection.extractor_type == "HTTP":
                    return _build_task_result(
                        "No observations were returned from the source system. "
                        "Confirm the configured source system has observations available for the requested time range.",
                        context,
                        stage=context.stage,
                    )
                return _build_task_result(
                    "The extractor returned no observations. Nothing to load.",
                    context,
                    stage=context.stage,
                )

            context.stage = "transform"
            logging.info("Starting transform")
            data = transformer_cls.transform(data, task_mappings)
            transform_summary = _describe_transformed_data(data)
            logging.info("Transform result: %s", transform_summary)
            if isinstance(data, pd.DataFrame) and "timestamp" in data.columns:
                bad = data["timestamp"].isna().sum()
                if bad:
                    raise EtlUserFacingError(
                        "One or more timestamps could not be read using the current format and timezone settings. "
                        "Confirm how dates appear in the source file and update the transformer configuration to match."
                    )
            if _is_empty(data):
                # hydroserverpy's CSVTransformer returns None on read errors (but logs ERROR).
                # Treat that as a failure to avoid misleading "produced no rows" messaging.
                last_err = _last_logged_error(context)
                if last_err and last_err.startswith("Error reading CSV data:"):
                    mapped_csv_error = _mapped_csv_error_from_log(last_err)
                    if mapped_csv_error:
                        raise EtlUserFacingError(mapped_csv_error)
                    raise EtlUserFacingError(
                        f"{last_err}. Check delimiter/headerRow/dataStartRow/identifierType settings "
                        "and confirm the upstream CSV columns match your task mappings."
                    )
                return _build_task_result(
                    "Transform produced no rows. Nothing to load.",
                    context,
                    stage=context.stage,
                )

            context.stage = "load"
            logging.info("Starting load")
            load_summary = loader_cls.load(data, task)
            logging.info(
                "Load result: loaded=%s available=%s cutoff=%s",
                getattr(load_summary, "observations_loaded", None),
                getattr(load_summary, "observations_available", None),
                getattr(load_summary, "cutoff", None),
            )

            return _build_task_result(
                _success_message(load_summary),
                context,
                stage=context.stage,
            )
        except Exception as e:
            mapped = user_facing_error_from_exception(
                e, transformer_raw=locals().get("transformer_raw")
            )
            if mapped:
                logging.error("%s", str(mapped))
                if mapped is e:
                    raise
                raise mapped from e
            logging.exception("ETL task failed during %s", context.stage)
            raise


@task_prerun.connect
def mark_etl_task_started(sender, task_id, kwargs, **extra):
    """
    Marks an ETL task as RUNNING.
    """

    if sender != run_etl_task:
        return

    try:
        TaskRun.objects.create(
            id=task_id,
            task_id=kwargs["task_id"],
            status="RUNNING",
            started_at=timezone.now(),
        )
    except IntegrityError:
        return


@task_postrun.connect
def update_next_run(sender, task_id, kwargs, **extra):
    if sender != run_etl_task:
        return

    try:
        task = Task.objects.select_related("periodic_task").get(pk=kwargs["task_id"])
    except Task.DoesNotExist:
        return

    if not task.periodic_task:
        task.next_run_at = None
        task.save(update_fields=["next_run_at"])
        return

    now = timezone.now()

    time_delta = task.periodic_task.schedule.remaining_estimate(now)
    time_delta = max(time_delta, timedelta(0))

    task.next_run_at = now + time_delta
    task.save(update_fields=["next_run_at"])


@task_success.connect
def mark_etl_task_success(sender, result, **extra):
    """
    Marks an ETL task as SUCCESS.
    """

    if sender != run_etl_task:
        return

    context = TASK_RUN_CONTEXT.pop(sender.request.id, None)

    try:
        task_run = TaskRun.objects.get(id=sender.request.id)
    except TaskRun.DoesNotExist:
        return

    if not isinstance(result, dict):
        result = {"message": str(result)}

    result = _merge_result_with_context(result, context)
    if context and context.stage and "stage" not in result:
        result["stage"] = context.stage

    transformer_raw = task_transformer_raw(task_run.task)
    result = normalize_task_run_result(
        status="SUCCESS",
        result=result,
        transformer_raw=transformer_raw,
    )

    task_run.status = "SUCCESS"
    task_run.finished_at = timezone.now()
    task_run.result = result

    task_run.save(update_fields=["status", "finished_at", "result"])


@task_failure.connect
def mark_etl_task_failure(sender, task_id, einfo, exception, **extra):
    """
    Marks an ETL task as FAILED.
    """

    if sender != run_etl_task:
        return

    context = TASK_RUN_CONTEXT.pop(task_id, None)

    try:
        task_run = TaskRun.objects.get(id=task_id)
    except TaskRun.DoesNotExist:
        return

    stage = context.stage if context else None
    mapped = user_facing_error_from_exception(exception)
    if mapped:
        # User-facing errors are already stage-aware and readable; don't prepend robotic prefixes.
        message = str(mapped)
    else:
        if stage and stage.lower() == "setup":
            message = f"Setup failed: {exception}"
        else:
            message = f"Failed during {stage}: {exception}" if stage else f"{exception}"

    task_run.status = "FAILURE"
    task_run.finished_at = timezone.now()
    transformer_raw = task_transformer_raw(task_run.task)
    task_run.result = normalize_task_run_result(
        status="FAILURE",
        result=_build_task_result(
            message,
            context,
            stage=stage,
            traceback=einfo.traceback,
        ),
        transformer_raw=transformer_raw,
    )

    task_run.save(update_fields=["status", "finished_at", "result"])


@shared_task(bind=True, expires=10, name="etl.tasks.cleanup_etl_task_runs")
def cleanup_etl_task_runs(self, days=14):
    """
    Celery task to run the cleanup_etl_task_runs management command.
    """

    call_command("cleanup_etl_task_runs", f"--days={days}")
