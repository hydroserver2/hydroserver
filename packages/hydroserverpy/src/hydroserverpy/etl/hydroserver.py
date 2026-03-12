from datetime import datetime, timezone
from pydantic.alias_generators import to_snake
from typing import Optional
from hydroserverpy.api.models import Task, DataConnection
from hydroserverpy.etl import extractors, transformers, loaders, ETLPipeline
from hydroserverpy.etl.transformers import ETLDataMapping, ETLTargetPath
from hydroserverpy.etl.operations import (DataOperation, RatingCurveDataOperation, ArithmeticExpressionOperation,
                                          TemporalAggregationOperation)
from hydroserverpy.etl.models import Timestamp


def normalize_timestamp_kwargs(**kwargs) -> dict:
    """
    Convert a raw timestamp configuration dict (as stored on a data connection
    or placeholder variable) into keyword arguments suitable for constructing
    a Timestamp model.
    """

    timezone_map = {
        "fixedOffset": "offset",
        "daylightSavings": "iana",
    }

    return {
        "timestamp_type": "custom" if kwargs["format"] == "custom" else "iso",
        "timestamp_format": kwargs.get("customFormat"),
        "timezone_type": timezone_map.get(  # noqa
            kwargs["timezoneMode"], "utc"
        ),
        "timezone": kwargs.get("timezone")
    }


def resolve_runtime_variables(
    placeholder_variables: list,
    etl_variables: dict,
    earliest_loaded_through: Optional[datetime],
    execution_time: datetime,
) -> dict:
    """
    Resolve a list of placeholder variable definitions into a flat dict of
    name → string value, suitable for passing as runtime template variables
    to an ETL pipeline component.
    """

    runtime_variables = {}

    for placeholder_variable in placeholder_variables:
        if placeholder_variable["type"] == "runTime":
            timestamp_parser = Timestamp(
                **normalize_timestamp_kwargs(**placeholder_variable["timestamp"])
            )

            if placeholder_variable["runTimeValue"] == "latestObservationTimestamp":
                dt = earliest_loaded_through if earliest_loaded_through is not None \
                    else datetime(1970, 1, 1, tzinfo=timezone.utc)
                runtime_variables[placeholder_variable["name"]] = timestamp_parser.to_string(dt)
            else:
                runtime_variables[placeholder_variable["name"]] = timestamp_parser.to_string(execution_time)

        else:
            runtime_variables[placeholder_variable["name"]] = etl_variables[placeholder_variable["name"]]

    return runtime_variables


def resolve_data_operations(raw_etl_target_path: dict) -> list[DataOperation]:
    """
    Parse the raw 'dataTransformations' list from a target path dict into a
    list of typed DataOperation instances.
    """

    resolved_data_operations = []

    for data_operation in raw_etl_target_path.get("dataTransformations", []):
        if data_operation["type"] == "expression":
            resolved_data_operations.append(ArithmeticExpressionOperation(
                target_identifier=raw_etl_target_path["targetIdentifier"],
                expression=data_operation["expression"],
            ))
        elif data_operation["type"] == "rating_curve":
            resolved_data_operations.append(RatingCurveDataOperation(
                target_identifier=raw_etl_target_path["targetIdentifier"],
                rating_curve_url=data_operation["ratingCurveUrl"],
            ))
        elif data_operation["type"] == "aggregation":
            timezone_kwargs = normalize_timestamp_kwargs(format="iso", **data_operation)
            aggregation_mapping = {
                "simple_mean": "simple_mean",
                "time_weighted_daily_mean": "time_weighted_mean",
                "last_value_of_day": "last_value_of_period",
            }
            resolved_data_operations.append(TemporalAggregationOperation(
                target_identifier=raw_etl_target_path["targetIdentifier"],
                aggregation_statistic=aggregation_mapping[data_operation["aggregationStatistic"]],
                timezone_type=timezone_kwargs.get("timezone_type"),
                timezone=timezone_kwargs.get("timezone"),
            ))

    return resolved_data_operations


def build_hydroserver_pipeline(
    task: Task,
    data_connection: DataConnection,
    data_mappings:  list[dict],
    extractor_cls: Optional[type[extractors.Extractor]] = None,
    transformer_cls: Optional[type[transformers.Transformer]] = None,
    loader_cls: Optional[type[loaders.Loader]] = None,
) -> tuple[ETLPipeline, list[ETLDataMapping], dict]:
    """
    Construct an ETLPipeline, its data mappings, and resolved runtime template
    variables from a HydroServer Task record.

    Component classes are resolved by name from the task's data connection
    settings unless overridden via the optional cls arguments, which are
    intended for testing.

    Settings dicts are copied before placeholderVariables are extracted so
    that the task's data connection settings are not mutated in place.
    Remaining keys are converted from camelCase to snake_case before being
    passed to each component constructor.

    Runtime variables are resolved against the current execution time and the
    earliest loaded-through timestamp across all target datastreams. If no
    targets have been loaded yet, execution_time is used as the fallback for
    'latestObservationTimestamp' variables.

    Returns a 3-tuple of (pipeline, data_mappings, runtime_variables). The
    pipeline should be run by the caller with the returned data_mappings and
    runtime_variables passed to pipeline.run().
    """

    if extractor_cls is None:
        extractor_cls = getattr(extractors, f"{data_connection.extractor_type}Extractor")

    if transformer_cls is None:
        transformer_cls = getattr(transformers, f"{data_connection.transformer_type}Transformer")

    if loader_cls is None:
        loader_cls = getattr(loaders, f"{data_connection.loader_type}Loader")

    extractor_settings = dict(data_connection.extractor_settings) if data_connection else {}
    transformer_settings = dict(data_connection.transformer_settings) if data_connection else {}
    loader_settings = dict(data_connection.loader_settings) if data_connection else {}

    extractor_placeholders = extractor_settings.pop("placeholderVariables", [])
    extractor_variables = getattr(task, "extractor_settings", None) or getattr(task, "extractor_variables", {})

    transformer_placeholders = transformer_settings.pop("placeholderVariables", [])
    transformer_variables = getattr(task, "transformer_settings", None) or getattr(task, "transformer_variables", {})

    loader_placeholders = loader_settings.pop("placeholderVariables", [])
    loader_variables = getattr(task, "loader_settings", None) or getattr(task, "loader_variables", {})

    extractor: extractors.Extractor = extractor_cls(
        **{to_snake(k): v for k, v in extractor_settings.items()}
    )

    if task.task_type == "Aggregation":
        timestamp_settings = {
            "key": "phenomenon_time",
            "format": "iso",
            "timezoneMode": "utc"
        }
    else:
        timestamp_settings = transformer_settings.pop("timestamp", {})

    transformer_settings = {
        ("jmespath" if k == "JMESPath" else to_snake(k)): v
        for k, v in transformer_settings.items()
    }

    transformer: transformers.Transformer = transformer_cls(
        timestamp_key=timestamp_settings["key"],
        **transformer_settings,
        **normalize_timestamp_kwargs(**timestamp_settings)
    )

    loader: loaders.Loader = loader_cls(
        **{to_snake(k): v for k, v in loader_settings.items()}
    )

    etl_data_mappings = [
        ETLDataMapping(
            source_identifier=mapping["sourceIdentifier"],
            target_paths=[ETLTargetPath(
                target_identifier=path["targetIdentifier"],
                data_operations=resolve_data_operations(path)
            ) for path in mapping["paths"]]
        ) for mapping in data_mappings
    ]

    execution_time = datetime.now(timezone.utc)
    earliest_loaded_through = loader.earliest_loaded_through(
        target_identifiers=[
            path["targetIdentifier"]
            for mapping in data_mappings
            for path in mapping["paths"]
        ]
    )

    runtime_variables = {
        **resolve_runtime_variables(
            placeholder_variables=extractor_placeholders,
            etl_variables=extractor_variables,
            execution_time=execution_time,
            earliest_loaded_through=earliest_loaded_through,
        ),
        **resolve_runtime_variables(
            placeholder_variables=transformer_placeholders,
            etl_variables=transformer_variables,
            execution_time=execution_time,
            earliest_loaded_through=earliest_loaded_through,
        ),
        **resolve_runtime_variables(
            placeholder_variables=loader_placeholders,
            etl_variables=loader_variables,
            execution_time=execution_time,
            earliest_loaded_through=earliest_loaded_through,
        ),
    }

    etl_pipeline = ETLPipeline(
        extractor=extractor,
        transformer=transformer,
        loader=loader,
    )

    return etl_pipeline, etl_data_mappings, runtime_variables
