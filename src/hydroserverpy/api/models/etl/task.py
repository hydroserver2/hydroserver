from __future__ import annotations
from functools import cached_property
import uuid
import logging
import croniter
import pandas as pd
from typing import ClassVar, TYPE_CHECKING, List, Optional, Literal, Union
from datetime import datetime, timedelta, timezone
from pydantic import Field, AliasPath, AliasChoices, TypeAdapter
from hydroserverpy.etl.factories import extractor_factory, transformer_factory, loader_factory
from hydroserverpy.etl.loaders.hydroserver_loader import LoadSummary
from hydroserverpy.etl.etl_configuration import ExtractorConfig, TransformerConfig, LoaderConfig, SourceTargetMapping, MappingPath
from hydroserverpy.etl.aggregation import (
    aggregate_daily_window,
    closed_window_end_utc,
    first_window_start_utc,
    iter_daily_windows_utc,
    next_window_start_utc,
    parse_aggregation_transformation,
)
from ..base import HydroServerBaseModel
from .orchestration_system import OrchestrationSystem
from .data_connection import DataConnection
from .run import TaskRun


if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class Task(HydroServerBaseModel):
    name: str = Field(..., max_length=255)
    task_type: Literal["ETL", "Aggregation"] = Field("ETL", alias="type")
    extractor_settings: dict = Field(default_factory=dict, alias="extractorSettings")
    transformer_settings: dict = Field(default_factory=dict, alias="transformerSettings")
    loader_settings: dict = Field(default_factory=dict, alias="loaderSettings")
    data_connection_id: Optional[uuid.UUID] = Field(
        None, validation_alias=AliasChoices("dataConnectionId", AliasPath("dataConnection", "id"))
    )
    orchestration_system_id: uuid.UUID = Field(
        None, validation_alias=AliasChoices("orchestrationSystemId", AliasPath("orchestrationSystem", "id"))
    )
    workspace_id: uuid.UUID = Field(
        None, validation_alias=AliasChoices("workspaceId", AliasPath("workspace", "id"))
    )
    start_time: Optional[datetime] = Field(None, validation_alias=AliasPath("schedule", "startTime"))
    next_run_at: Optional[datetime] = Field(None, validation_alias=AliasPath("schedule", "nextRunAt"))
    paused: bool = Field(False, validation_alias=AliasPath("schedule", "paused"))
    interval: Optional[int] = Field(None, gt=0, validation_alias=AliasPath("schedule", "interval"))
    interval_period: Optional[Literal["minutes", "hours", "days"]] = Field(
        None, validation_alias=AliasPath("schedule", "intervalPeriod")
    )
    crontab: Optional[str] = Field(None, validation_alias=AliasPath("schedule", "crontab"))
    latest_run: Optional[TaskRun] = None
    mappings: List[dict]

    _editable_fields: ClassVar[set[str]] = {
        "name",
        "task_type",
        "extractor_settings",
        "transformer_settings",
        "loader_settings",
        "data_connection_id",
        "orchestration_system_id",
        "start_time",
        "next_run_at",
        "paused",
        "interval",
        "interval_period",
        "crontab",
        "mappings"
    }

    def __init__(self, client: HydroServer, **data):
        super().__init__(client=client, service=client.tasks, **data)

    @classmethod
    def get_route(cls):
        return "etl-tasks"

    @cached_property
    def workspace(self) -> Workspace:
        return self.client.workspaces.get(uid=self.workspace_id)

    @cached_property
    def orchestration_system(self) -> Optional[OrchestrationSystem]:
        return self.client.orchestrationsystems.get(uid=self.orchestration_system_id)

    @cached_property
    def data_connection(self) -> Optional[DataConnection]:
        if not self.data_connection_id:
            return None
        return self.client.dataconnections.get(uid=self.data_connection_id)

    def get_task_runs(
        self,
        page: int = ...,
        page_size: int = 100,
        order_by: List[str] = ...,
        status: str = ...,
        started_at_max: datetime = ...,
        started_at_min: datetime = ...,
        finished_at_max: datetime = ...,
        finished_at_min: datetime = ...,
    ):
        """Get a collection of task runs associated with this task."""

        return self.client.tasks.get_task_runs(
            uid=self.uid,
            page=page,
            page_size=page_size,
            order_by=order_by,
            status=status,
            started_at_max=started_at_max,
            started_at_min=started_at_min,
            finished_at_max=finished_at_max,
            finished_at_min=finished_at_min,
        )

    def create_task_run(
        self,
        status: Literal["RUNNING", "SUCCESS", "FAILURE"],
        started_at: datetime,
        finished_at: datetime = ...,
        result: dict = ...,
    ):
        """Create a new task run for this task."""

        return self.client.tasks.create_task_run(
            uid=self.uid,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            result=result,
        )

    def get_task_run(
        self,
        uid: Union[uuid.UUID, str],
    ):
        """Get a task run record for this task."""

        return self.client.tasks.get_task_run(uid=self.uid, task_run_id=uid)

    def update_task_run(
        self,
        uid: Union[uuid.UUID, str],
        status: Literal["RUNNING", "SUCCESS", "FAILURE"] = ...,
        started_at: datetime = ...,
        finished_at: datetime = ...,
        result: dict = ...,
    ):
        """Update a task run record of this task."""

        return self.client.tasks.update_task_run(
            uid=self.uid,
            task_run_id=uid,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            result=result,
        )

    def delete_task_run(
        self,
        uid: Union[uuid.UUID, str],
    ):
        """Delete a task run record of this task."""

        return self.client.tasks.delete_task_run(uid=self.uid, task_run_id=uid)

    def run(self):
        """Trigger HydroServer to run this task."""

        return self.client.tasks.run(uid=self.uid)

    def run_local(self):
        """Run this task locally."""

        if self.paused is True:
            return

        task_run = self.create_task_run(status="RUNNING", started_at=datetime.now(timezone.utc))
        runtime_source_uri: Optional[str] = None

        try:
            if self.task_type == "Aggregation":
                summary = self._run_local_aggregation()
                if summary["rows_loaded"] == 0:
                    self._update_status(
                        task_run,
                        True,
                        "No new closed daily windows were available for aggregation.",
                    )
                else:
                    self._update_status(
                        task_run,
                        True,
                        (
                            f"Aggregated {summary['days_loaded']} day(s) and loaded "
                            f"{summary['rows_loaded']} observation(s) across {summary['mappings_loaded']} mapping(s)."
                        ),
                    )
                return

            if not self.data_connection:
                raise ValueError("ETL tasks require a data connection.")

            extractor_cls = extractor_factory(TypeAdapter(ExtractorConfig).validate_python({
                "type": self.data_connection.extractor_type,
                **self.data_connection.extractor_settings
            }))
            transformer_cls = transformer_factory(TypeAdapter(TransformerConfig).validate_python({
                "type": self.data_connection.transformer_type,
                **self.data_connection.transformer_settings
            }))
            loader_cls = loader_factory(TypeAdapter(LoaderConfig).validate_python({
                "type": self.data_connection.loader_type,
                **self.data_connection.loader_settings
            }), self.client, str(self.uid))

            logging.info("Starting extract")

            task_mappings = [
                SourceTargetMapping(
                    source_identifier=task_mapping["sourceIdentifier"],
                    paths=[
                        MappingPath(
                            target_identifier=task_mapping_path["targetIdentifier"],
                            data_transformations=task_mapping_path["dataTransformations"],
                        ) for task_mapping_path in task_mapping["paths"]
                    ]
                ) for task_mapping in self.mappings
            ]

            data = extractor_cls.extract(self, loader_cls)
            runtime_source_uri = getattr(extractor_cls, "runtime_source_uri", None)
            if self.is_empty(data):
                self._update_status(
                    task_run,
                    True,
                    "No data returned from the extractor",
                    runtime_source_uri=runtime_source_uri,
                )
                return

            logging.info("Starting transform")
            data = transformer_cls.transform(data, task_mappings)
            if self.is_empty(data):
                self._update_status(
                    task_run,
                    True,
                    "No data returned from the transformer",
                    runtime_source_uri=runtime_source_uri,
                )
                return

            logging.info("Starting load")
            load_summary = loader_cls.load(data, self)
            self._update_status(
                task_run,
                True,
                self._success_message(load_summary),
                runtime_source_uri=runtime_source_uri,
            )
        except Exception as e:
            self._update_status(
                task_run, False, str(e), runtime_source_uri=runtime_source_uri
            )

    @staticmethod
    def is_empty(data):
        if data is None:
            return True

        if isinstance(data, pd.DataFrame) and data.empty:
            return True

        return False

    def _fetch_observation_points(
        self,
        source_datastream_id: str,
        query_start_utc: datetime,
        query_end_utc: datetime,
    ) -> tuple[list[datetime], list[float]]:
        observations = self.client.datastreams.get_observations(
            uid=source_datastream_id,
            order_by=["phenomenonTime"],
            phenomenon_time_min=query_start_utc,
            phenomenon_time_max=query_end_utc,
            fetch_all=True,
        ).dataframe

        prev_df = self.client.datastreams.get_observations(
            uid=source_datastream_id,
            order_by=["-phenomenonTime"],
            page=1,
            page_size=1,
            phenomenon_time_max=query_start_utc,
            fetch_all=False,
        ).dataframe
        next_df = self.client.datastreams.get_observations(
            uid=source_datastream_id,
            order_by=["phenomenonTime"],
            page=1,
            page_size=1,
            phenomenon_time_min=query_end_utc,
            fetch_all=False,
        ).dataframe

        frames = [df for df in [prev_df, observations, next_df] if not df.empty]
        if not frames:
            return [], []

        merged = pd.concat(frames, ignore_index=True)
        merged = merged[["phenomenon_time", "result"]].dropna(subset=["phenomenon_time", "result"])
        merged["phenomenon_time"] = pd.to_datetime(
            merged["phenomenon_time"], utc=True, errors="coerce"
        )
        merged["result"] = pd.to_numeric(merged["result"], errors="coerce")
        merged = merged.dropna(subset=["phenomenon_time", "result"])
        merged = merged.sort_values("phenomenon_time")
        merged = merged.drop_duplicates(subset=["phenomenon_time"], keep="last")

        timestamps = [
            ts.to_pydatetime() for ts in merged["phenomenon_time"].tolist()
        ]
        values = merged["result"].astype(float).tolist()
        return timestamps, values

    def _run_local_aggregation(self) -> dict[str, int]:
        mappings = self.mappings or []
        if len(mappings) < 1:
            raise ValueError(
                "Aggregation tasks must include at least one mapping."
            )

        rows_loaded = 0
        mappings_loaded = 0
        days_loaded = 0

        for mapping in mappings:
            source_id = str(mapping["sourceIdentifier"])
            paths = mapping.get("paths", []) or []
            if len(paths) != 1:
                raise ValueError(
                    "Aggregation mappings must include exactly one target path per source."
                )

            path = paths[0]
            target_id = str(path["targetIdentifier"])
            transformations = path.get("dataTransformations", []) or []
            if not isinstance(transformations, list) or len(transformations) != 1:
                raise ValueError(
                    "Aggregation mappings must include exactly one aggregation transformation."
                )
            transformation = parse_aggregation_transformation(transformations[0])

            source_datastream = self.client.datastreams.get(uid=source_id)
            target_datastream = self.client.datastreams.get(uid=target_id)

            source_end = source_datastream.phenomenon_end_time
            if source_end is None:
                continue

            closed_end = closed_window_end_utc(source_end, transformation)
            destination_end = target_datastream.phenomenon_end_time
            source_begin = source_datastream.phenomenon_begin_time
            if source_begin is None:
                continue

            query_start = first_window_start_utc(source_begin, transformation)
            if destination_end is None:
                start_window = query_start
            else:
                start_window = next_window_start_utc(destination_end, transformation)

            if start_window >= closed_end:
                continue

            timestamps, values = self._fetch_observation_points(
                source_datastream_id=source_id,
                query_start_utc=query_start,
                query_end_utc=closed_end,
            )
            if not timestamps:
                continue

            output_rows: list[dict[str, object]] = []
            for day_start, day_end, _ in iter_daily_windows_utc(
                start_window,
                closed_end,
                transformation,
            ):
                value = aggregate_daily_window(
                    timestamps=timestamps,
                    values=values,
                    window_start_utc=day_start,
                    window_end_utc=day_end,
                    statistic=transformation.aggregation_statistic,
                )
                if value is None:
                    continue
                output_rows.append(
                    {
                        "phenomenon_time": day_start,
                        "result": float(value),
                    }
                )

            if not output_rows:
                continue

            output_df = pd.DataFrame(output_rows)
            self.client.datastreams.load_observations(
                uid=target_id,
                observations=output_df,
                mode="append",
            )

            rows_loaded += len(output_rows)
            days_loaded += len(output_rows)
            mappings_loaded += 1

        return {
            "rows_loaded": rows_loaded,
            "days_loaded": days_loaded,
            "mappings_loaded": mappings_loaded,
        }

    def _update_status(
        self,
        task_run: TaskRun,
        success: bool,
        msg: str,
        runtime_source_uri: Optional[str] = None,
    ):
        result = {"message": msg}
        if runtime_source_uri:
            result.update(
                {
                    "runtimeSourceUri": runtime_source_uri,
                    "runtime_source_uri": runtime_source_uri,
                    "runtimeUrl": runtime_source_uri,
                    "runtime_url": runtime_source_uri,
                }
            )

        self.update_task_run(
            task_run.id,
            status="SUCCESS" if success else "FAILURE",
            finished_at=datetime.now(timezone.utc),
            result=result
        )
        self.next_run_at = self._next_run()
        self.save()

    @staticmethod
    def _success_message(load: Optional[LoadSummary]) -> str:
        if not load:
            return "OK"

        loaded = load.observations_loaded
        if loaded == 0:
            if load.timestamps_total and load.timestamps_after_cutoff == 0:
                if load.cutoff:
                    return (
                        "Already up to date - no new observations loaded "
                        f"(all timestamps were at or before {load.cutoff})."
                    )
                return "Already up to date - no new observations loaded (all timestamps were at or before the cutoff)."
            if load.observations_available == 0:
                return "Already up to date - no new observations loaded."
            return "No new observations were loaded."

        if load.datastreams_loaded:
            return (
                f"Load completed successfully ({loaded} rows across {load.datastreams_loaded} datastreams)."
            )
        return f"Load completed successfully ({loaded} rows loaded)."

    def _next_run(self) -> Optional[str]:
        now = datetime.now(timezone.utc)
        if cron := self.crontab:
            return croniter.croniter(cron, now).get_next(datetime).isoformat()
        if iv := self.interval:
            unit = self.interval_period or "minutes"
            return (now + timedelta(**{unit: iv})).isoformat()
        return None
