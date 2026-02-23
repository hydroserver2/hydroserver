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
from domains.sta.models import Datastream, Observation
from domains.sta.services import ObservationService
from interfaces.api.schemas.observation import ObservationBulkPostBody
from .loader import HydroServerInternalLoader, LoadSummary
from .etl_errors import (
    EtlUserFacingError,
    user_facing_error_from_exception,
    user_facing_error_from_validation_error,
)
from .run_result_normalizer import normalize_task_run_result, task_transformer_raw
from .aggregation import (
    AggregationTransformation,
    aggregate_daily_window,
    closed_window_end_utc,
    first_window_start_utc,
    iter_daily_windows_utc,
    next_window_start_utc,
    parse_aggregation_transformation,
)
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


@dataclass(frozen=True)
class AggregationMapping:
    source_datastream_id: UUID
    target_datastream_id: UUID
    transformation: AggregationTransformation


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
observation_service = ObservationService()


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


def _parse_datastream_uuid(raw_value: Any, field_name: str) -> UUID:
    try:
        return UUID(str(raw_value))
    except (TypeError, ValueError) as exc:
        raise EtlUserFacingError(
            f"Aggregation mapping {field_name} must be a valid datastream UUID."
        ) from exc


def _extract_aggregation_mappings(task: Task) -> list[AggregationMapping]:
    task_mappings = list(task.mappings.all())
    if len(task_mappings) < 1:
        raise EtlUserFacingError(
            "Aggregation tasks must include at least one mapping."
        )

    mappings: list[AggregationMapping] = []
    for task_mapping in task_mappings:
        paths = list(task_mapping.paths.all())
        if len(paths) != 1:
            raise EtlUserFacingError(
                "Aggregation mappings must include exactly one target path per source."
            )

        path = paths[0]
        source_id = _parse_datastream_uuid(
            task_mapping.source_identifier, "sourceIdentifier"
        )
        target_id = _parse_datastream_uuid(
            path.target_identifier, "targetIdentifier"
        )

        transformations = path.data_transformations or []
        if not isinstance(transformations, list) or len(transformations) != 1:
            raise EtlUserFacingError(
                "Aggregation mappings must include exactly one aggregation transformation."
            )
        if not isinstance(transformations[0], dict):
            raise EtlUserFacingError("Invalid aggregation transformation payload.")

        try:
            transformation = parse_aggregation_transformation(transformations[0])
        except ValueError as exc:
            raise EtlUserFacingError(str(exc)) from exc

        mappings.append(
            AggregationMapping(
                source_datastream_id=source_id,
                target_datastream_id=target_id,
                transformation=transformation,
            )
        )

    return mappings


def _fetch_observation_points(
    source_datastream_id: UUID,
    query_start_utc: datetime,
    query_end_utc: datetime,
) -> tuple[list[datetime], list[float]]:
    points = list(
        Observation.objects.filter(
            datastream_id=source_datastream_id,
            phenomenon_time__gte=query_start_utc,
            phenomenon_time__lt=query_end_utc,
        )
        .order_by("phenomenon_time")
        .values_list("phenomenon_time", "result")
    )

    previous_point = (
        Observation.objects.filter(
            datastream_id=source_datastream_id,
            phenomenon_time__lt=query_start_utc,
        )
        .order_by("-phenomenon_time")
        .values_list("phenomenon_time", "result")
        .first()
    )
    if previous_point:
        points.insert(0, previous_point)

    next_point = (
        Observation.objects.filter(
            datastream_id=source_datastream_id,
            phenomenon_time__gte=query_end_utc,
        )
        .order_by("phenomenon_time")
        .values_list("phenomenon_time", "result")
        .first()
    )
    if next_point:
        points.append(next_point)

    cleaned: list[tuple[datetime, float]] = []
    for phenomenon_time, result in points:
        try:
            result_float = float(result)
        except (TypeError, ValueError):
            continue
        if not pd.notna(result_float):
            continue
        if cleaned and cleaned[-1][0] == phenomenon_time:
            cleaned[-1] = (phenomenon_time, result_float)
        else:
            cleaned.append((phenomenon_time, result_float))

    timestamps = [point[0] for point in cleaned]
    values = [point[1] for point in cleaned]
    return timestamps, values


def _load_aggregated_rows(task: Task, target_datastream_id: UUID, rows: list[list[Any]]):
    chunk_size = 5000
    for offset in range(0, len(rows), chunk_size):
        chunk = rows[offset:offset + chunk_size]
        payload = ObservationBulkPostBody(
            fields=["phenomenonTime", "result"],
            data=chunk,
        )
        observation_service.bulk_create(
            principal=task.workspace.owner,
            data=payload,
            datastream_id=target_datastream_id,
            mode="append",
        )


def _run_aggregation_task(task: Task, context: TaskRunContext) -> dict[str, Any]:
    context.stage = "aggregate"

    if not task.workspace.owner:
        raise EtlUserFacingError("Task workspace does not have an owner account.")

    mappings = _extract_aggregation_mappings(task)
    if not mappings:
        return _build_task_result(
            "Aggregation task has no mappings. Nothing to do.",
            context,
            stage=context.stage,
        )

    datastream_ids = {
        mapping.source_datastream_id for mapping in mappings
    } | {mapping.target_datastream_id for mapping in mappings}
    datastreams = Datastream.objects.filter(
        id__in=datastream_ids,
        thing__workspace_id=task.workspace_id,
    ).only("id", "name", "phenomenon_begin_time", "phenomenon_end_time")
    datastream_map = {datastream.id: datastream for datastream in datastreams}

    loaded_rows = 0
    loaded_mappings = 0
    loaded_days = 0
    mapping_summaries: list[dict[str, Any]] = []

    for mapping in mappings:
        source = datastream_map.get(mapping.source_datastream_id)
        target = datastream_map.get(mapping.target_datastream_id)

        if not source or not target:
            raise EtlUserFacingError(
                "Aggregation source and target datastreams must exist in the task workspace."
            )

        source_end = source.phenomenon_end_time
        if not source_end:
            logging.info(
                "Skipping mapping source=%s target=%s: source has no observations yet.",
                source.id,
                target.id,
            )
            mapping_summaries.append(
                {
                    "sourceDatastreamId": str(source.id),
                    "targetDatastreamId": str(target.id),
                    "status": "skipped",
                    "reason": "Source datastream has no observations.",
                    "rowsLoaded": 0,
                    "daysLoaded": 0,
                }
            )
            continue

        closed_end = closed_window_end_utc(source_end, mapping.transformation)
        destination_end = target.phenomenon_end_time

        source_begin = source.phenomenon_begin_time
        if not source_begin:
            logging.info(
                "Skipping mapping source=%s target=%s: source has no phenomenon_begin_time.",
                source.id,
                target.id,
            )
            mapping_summaries.append(
                {
                    "sourceDatastreamId": str(source.id),
                    "targetDatastreamId": str(target.id),
                    "status": "skipped",
                    "reason": "Source datastream has no observation history.",
                    "rowsLoaded": 0,
                    "daysLoaded": 0,
                }
            )
            continue

        query_start = first_window_start_utc(source_begin, mapping.transformation)
        if destination_end is None:
            start_window = query_start
        else:
            start_window = next_window_start_utc(destination_end, mapping.transformation)

        if start_window >= closed_end:
            logging.info(
                "Skipping mapping source=%s target=%s: no new closed daily windows.",
                source.id,
                target.id,
            )
            mapping_summaries.append(
                {
                    "sourceDatastreamId": str(source.id),
                    "targetDatastreamId": str(target.id),
                    "status": "up_to_date",
                    "reason": "No new closed daily windows.",
                    "rowsLoaded": 0,
                    "daysLoaded": 0,
                }
            )
            continue

        timestamps, values = _fetch_observation_points(
            source_datastream_id=source.id,
            query_start_utc=query_start,
            query_end_utc=closed_end,
        )
        if not timestamps:
            logging.info(
                "Skipping mapping source=%s target=%s: no source observations in query range.",
                source.id,
                target.id,
            )
            mapping_summaries.append(
                {
                    "sourceDatastreamId": str(source.id),
                    "targetDatastreamId": str(target.id),
                    "status": "skipped",
                    "reason": "No source observations available for aggregation.",
                    "rowsLoaded": 0,
                    "daysLoaded": 0,
                }
            )
            continue

        rows: list[list[Any]] = []
        for day_start, day_end, _ in iter_daily_windows_utc(
            start_window,
            closed_end,
            mapping.transformation,
        ):
            value = aggregate_daily_window(
                timestamps=timestamps,
                values=values,
                window_start_utc=day_start,
                window_end_utc=day_end,
                statistic=mapping.transformation.aggregation_statistic,
            )
            if value is None:
                continue
            rows.append([day_start, float(value)])

        if not rows:
            mapping_summaries.append(
                {
                    "sourceDatastreamId": str(source.id),
                    "targetDatastreamId": str(target.id),
                    "status": "up_to_date",
                    "reason": "No complete daily windows contained source observations.",
                    "rowsLoaded": 0,
                    "daysLoaded": 0,
                }
            )
            continue

        _load_aggregated_rows(task=task, target_datastream_id=target.id, rows=rows)

        loaded_rows += len(rows)
        loaded_days += len(rows)
        loaded_mappings += 1

        logging.info(
            "Aggregated %s day(s) for mapping source=%s target=%s statistic=%s.",
            len(rows),
            source.id,
            target.id,
            mapping.transformation.aggregation_statistic,
        )
        mapping_summaries.append(
            {
                "sourceDatastreamId": str(source.id),
                "targetDatastreamId": str(target.id),
                "status": "loaded",
                "rowsLoaded": len(rows),
                "daysLoaded": len(rows),
                "statistic": mapping.transformation.aggregation_statistic,
            }
        )

    if loaded_rows == 0:
        result = _build_task_result(
            "No new closed daily windows were available for aggregation.",
            context,
            stage=context.stage,
        )
    else:
        result = _build_task_result(
            f"Aggregated {loaded_days} day(s) and loaded {loaded_rows} observation(s) across {loaded_mappings} mapping(s).",
            context,
            stage=context.stage,
        )

    result["aggregation"] = {
        "mappingsProcessed": len(mappings),
        "mappingsLoaded": loaded_mappings,
        "daysLoaded": loaded_days,
        "rowsLoaded": loaded_rows,
        "mappings": mapping_summaries,
    }
    return result


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
                Task.objects.select_related("data_connection", "workspace")
                .prefetch_related("mappings", "mappings__paths")
                .get(pk=UUID(task_id))
            )

            context.task_meta = {
                "id": str(task.id),
                "name": task.name,
                "type": task.task_type,
            }
            if task.data_connection_id:
                context.task_meta["data_connection_id"] = str(task.data_connection_id)
                context.task_meta["data_connection_name"] = task.data_connection.name

            context.stage = "setup"
            if task.task_type == "Aggregation":
                logging.info("Starting aggregation task")
                return _run_aggregation_task(task, context)

            if not task.data_connection:
                raise EtlUserFacingError("ETL tasks require a data connection.")

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
