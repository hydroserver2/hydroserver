from uuid import UUID
from datetime import datetime, timedelta, timezone

from celery import shared_task
from pydantic import ValidationError
from pydantic.alias_generators import to_camel

from interfaces.api.services.sta.datastream import DatastreamAPIService
from processing.etl.models import EtlTask
from processing.etl.loader import HydroServerInternalLoader

from hydroserverpy.etl import ETLPipeline
from hydroserverpy.etl.extractors import HTTPExtractor
from hydroserverpy.etl.transformers import CSVTransformer, JSONTransformer, ETLDataMapping, ETLTargetPath
from hydroserverpy.etl.models import Timestamp
from hydroserverpy.etl.exceptions import ETLError
from hydroserverpy.etl.user_facing_errors import coerce_known_etl_error


datastream_service = DatastreamAPIService()


@shared_task(bind=True, name="processing.etl.tasks.run_etl_task")
def run_etl_task(self, task_id: str, run_id: str | None = None):
    """
    Runs a HydroServer ETL task based on the task configuration provided.
    """

    try:
        task: EtlTask = (
            EtlTask.objects
            .select_related("data_connection__payload", "data_connection__workspace__owner")
            .prefetch_related("etl_mappings__target_datastream", "data_connection__placeholder_variables")
            .get(pk=UUID(task_id))
        )

        data_connection = task.data_connection
        etl_mappings = task.etl_mappings.select_related("target_datastream").all()

        for etl_mapping in etl_mappings:
            datastream_service.update_observation_statistics(
                datastream=etl_mapping.target_datastream,
                fields=["phenomenon_end_time"],
            )

        extractor = HTTPExtractor(
            source_uri=data_connection.source_url,
            auth_header_name=data_connection.auth_header_name,
            auth_header_value=data_connection.auth_header_value
        )

        timestamp = Timestamp(
            timestamp_type="custom" if data_connection.payload.timestamp_format is not None else "iso",
            timestamp_format=data_connection.payload.timestamp_format,
            timezone_type=data_connection.timezone_type or "utc",  # noqa
            timezone=data_connection.timezone,
        )

        if data_connection.payload.payload_type == "CSV":
            transformer = CSVTransformer(
                **timestamp.model_dump(),
                timestamp_key=data_connection.payload.timestamp_key,
                header_row=data_connection.payload.header_row,
                data_start_row=data_connection.payload.data_start_row,
                delimiter=data_connection.payload.delimiter,  # noqa
                identifier_type="index" if data_connection.payload.header_row is None else "name",
            )

        elif data_connection.payload.payload_type == "JSON":
            try:
                transformer = JSONTransformer(
                    **timestamp.model_dump(),
                    timestamp_key=data_connection.payload.timestamp_key,
                    jmespath=data_connection.payload.jmespath
                )
            except ValidationError as exc:
                raise coerce_known_etl_error(exc, component="transformer") from exc

        else:
            raise NotImplementedError(
                f"Unsupported payload settings for transformer: {str(data_connection.payload.payload_type)}"
            )

        loader = HydroServerInternalLoader()

        etl_pipeline = ETLPipeline(
            extractor=extractor,
            transformer=transformer,
            loader=loader,
        )

        execution_time = datetime.now(timezone.utc)
        earliest_loaded_through = loader.earliest_loaded_through(
            target_identifiers=[str(etl_mapping.target_datastream_id) for etl_mapping in etl_mappings]
        )

        placeholder_timestamps = {"run_time": execution_time, "latest_observation_timestamp": earliest_loaded_through}
        payload = data_connection.payload

        for side in ("start", "end"):
            anchor = getattr(payload, f"data_ingestion_window_{side}_anchor")
            boundary = (
                getattr(payload, f"data_ingestion_window_{side}_timestamp")
                if anchor == "fixed_timestamp" else placeholder_timestamps.get(anchor)
            )
            if anchor == "fixed_timestamp" and boundary is None:
                raise ValueError(
                    f"data_ingestion_window_{side}_timestamp is required when "
                    f"data_ingestion_window_{side}_anchor is 'fixed_timestamp'."
                )
            lookback = getattr(payload, f"data_ingestion_window_{side}_lookback")
            lookback_unit = getattr(payload, f"data_ingestion_window_{side}_lookback_unit")
            if boundary is not None and lookback and lookback_unit:
                boundary -= timedelta(**{lookback_unit: lookback})
            placeholder_timestamps[f"window_{side}"] = boundary

        data_ingestion_window_start = placeholder_timestamps["window_start"]
        data_ingestion_window_end = placeholder_timestamps["window_end"]

        placeholder_kwargs = {}
        for pv in data_connection.placeholder_variables.all():
            if pv.variable_type == "per_task":
                placeholder_kwargs[pv.name] = task.task_variables.get(pv.name)
            elif pv.variable_type in placeholder_timestamps:
                dt = placeholder_timestamps[pv.variable_type]
                pv_timestamp = (
                    Timestamp(
                        timestamp_type="custom",
                        timestamp_format=pv.timestamp_format,
                        timezone_type=data_connection.timezone_type,  # noqa
                        timezone=data_connection.timezone,
                    ) if pv.timestamp_format else timestamp
                )
                placeholder_kwargs[pv.name] = pv_timestamp.to_string(dt) if dt is not None else None

        context = etl_pipeline.run(
            raise_on_error=False,
            task_instance=task,
            data_mappings=[
                ETLDataMapping(
                    source_identifier=mapping.source_identifier,
                    target_paths=[
                        ETLTargetPath(
                            target_identifier=str(mapping.target_datastream_id),
                        )
                    ],
                ) for mapping in etl_mappings
            ],
            data_ingestion_window_start=data_ingestion_window_start,
            data_ingestion_window_end=data_ingestion_window_end,
            **placeholder_kwargs,
        )

        runtime_variables = {
            "extractor": {to_camel(k): v for k, v in context.runtime_variables.get("extractor", {}).items()},
            "transformer": {to_camel(k): v for k, v in context.runtime_variables.get("transformer", {}).items()},
            "loader": {to_camel(k): v for k, v in context.runtime_variables.get("loader", {}).items()}
        }

        if context.exception:
            context.exception.result = {
                "stage": str(context.stage),
                "runtimeVariables": runtime_variables,
            }
            raise context.exception
        elif context.results.values_loaded_total == 0:
            message = "Already up-to-date. No new observations were loaded."
        else:
            message = (
                f"Loaded {context.results.values_loaded_total} total observation(s) "
                f"into {context.results.success_count} datastream(s)."
            )

        result = {
            "message": message,
            "stage": str(context.stage),
            "runtimeVariables": runtime_variables,
        }
    except ETLError as e:
        raise e
    except Exception as e:
        raise Exception("Encountered an unexpected ETL error.") from e

    return result
