import uuid
import uuid6
from datetime import datetime, timezone
from typing import Optional, Union, Literal

from pydantic import Field, ConfigDict, validate_call
from django.db import transaction
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector, SearchQuery

from core.types import Unset
from core.iam.models import APIKey, Workspace
from core.service import ServiceUtils
from processing.orchestration.services import TaskService
from processing.etl.models import EtlTask, EtlMapping, DataConnection
from processing.etl.loader import HydroServerInternalLoader

from hydroserverpy.etl import ETLPipeline
from hydroserverpy.etl.extractors import HTTPExtractor
from hydroserverpy.etl.transformers import CSVTransformer, JSONTransformer, ETLDataMapping, ETLTargetPath
from hydroserverpy.etl.models import Timestamp


User = get_user_model()


class EtlTaskService(TaskService[EtlTask], ServiceUtils):

    task_model = EtlTask

    order_by_fields = {
        "id", "name", "data_connection_id", "data_connection__name", "data_connection__workspace_id",
        "data_connection__workspace__name", "latest_run_status", "latest_run_started_at",
        "latest_run_finished_at",
    }

    def get(
        self,
        task: Union[uuid.UUID, EtlTask],
        action: Literal["view", "edit", "delete"] = "view",
        principal: User | APIKey | None | Unset = Unset,
    ) -> EtlTask:
        """Get an ETL task with related data and latest run annotations."""

        task = super().get(task=task, action=action, principal=principal)

        if isinstance(task.pk, uuid.UUID):
            task = (
                self.annotate_latest_run(self.task_model.objects)
                .select_related("data_connection__workspace", "periodic_task__crontab", "periodic_task__interval")
                .prefetch_related("etl_mappings")
                .get(pk=task.pk)
            )

        return task

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        principal: Optional[User | APIKey] = None,
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] = Field(default_factory=list),
        search_term: str | Unset = Unset,
        workspace: list[uuid.UUID | Workspace] | Unset = Unset,
        data_connection: list[uuid.UUID | DataConnection] | Unset = Unset,
        latest_run_status: list[str] | Unset = Unset,
        latest_run_started_at_min: datetime | Unset = Unset,
        latest_run_started_at_max: datetime | Unset = Unset,
        latest_run_finished_at_min: datetime | Unset = Unset,
        latest_run_finished_at_max: datetime | Unset = Unset,
    ) -> tuple[int, QuerySet[EtlTask]]:
        """
        Return a collection of ETL tasks.
        """

        queryset = self.task_model.objects
        queryset = self.annotate_latest_run(queryset)

        if search_term is not Unset:
            search_vector = SearchVector("name", "description", "data_connection__name")
            queryset = queryset.annotate(search=search_vector).filter(search=SearchQuery(search_term))

        if workspace is not Unset:
            queryset = queryset.filter(data_connection__workspace__in=[
                getattr(w, "pk", w) for w in workspace
            ])

        if data_connection is not Unset:
            queryset = queryset.filter(data_connection__in=[
                getattr(dc, "pk", dc) for dc in data_connection
            ])

        if latest_run_status is not Unset:
            queryset = queryset.filter(latest_run_status__in=latest_run_status)

        if latest_run_started_at_min is not Unset:
            queryset = queryset.filter(latest_run_started_at__gte=latest_run_started_at_min)

        if latest_run_started_at_max is not Unset:
            queryset = queryset.filter(latest_run_started_at__lte=latest_run_started_at_max)

        if latest_run_finished_at_min is not Unset:
            queryset = queryset.filter(latest_run_finished_at__gte=latest_run_finished_at_min)

        if latest_run_finished_at_max is not Unset:
            queryset = queryset.filter(latest_run_finished_at__lte=latest_run_finished_at_max)

        if not all(term.lstrip("-") in self.order_by_fields for term in order_by):
            raise ValueError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "-id")
        queryset = queryset.select_related(
            "data_connection__workspace", "periodic_task__crontab", "periodic_task__interval"
        ).prefetch_related("etl_mappings")
        queryset = queryset.visible(principal=principal).distinct()  # noqa

        count = queryset.count()
        offset = (page - 1) * page_size

        queryset = queryset[offset:offset + page_size]

        return count, queryset

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | APIKey,
        name: str,
        data_connection: Union[uuid.UUID, DataConnection],
        uid: uuid.UUID = Field(default_factory=uuid6.uuid7),
        description: str | None = None,
        runtime_variables: dict = Field(default_factory=dict),
        crontab: str | None = None,
        interval: int | None = None,
        interval_period: Literal["minutes", "hours", "days"] | None = None,
        start_time: datetime | None = None,
        enabled: bool = True,
        mappings: list[dict] = Field(default_factory=list),
    ) -> EtlTask:
        """
        Create an ETL task.
        """

        if isinstance(data_connection, uuid.UUID):
            try:
                data_connection = DataConnection.objects.get(pk=data_connection)
            except DataConnection.DoesNotExist:
                raise LookupError(f"Data connection with ID {str(data_connection)} does not exist.")

        if not self.task_model.can_principal_create(
            principal=principal, workspace=data_connection.workspace
        ):
            raise PermissionError("You do not have permission to create this task.")

        task = self.task_model.objects.create(
            pk=uid,
            name=name,
            description=description,
            data_connection=data_connection,
            runtime_variables=runtime_variables,
        )

        self.apply_schedule(
            task=task,
            crontab=crontab,
            interval=interval,
            interval_period=interval_period,
            start_time=start_time,
            enabled=enabled,
            celery_task_name="processing.etl.tasks.run_etl_task",
        )

        self.apply_mappings(task=task, mappings=mappings)

        return self.get(task.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        task: Union[uuid.UUID, EtlTask],
        principal: User | APIKey,
        name: str | Unset = Unset,
        description: str | None | Unset = Unset,
        runtime_variables: dict | Unset = Unset,
        crontab: str | None | Unset = Unset,
        interval: int | None | Unset = Unset,
        interval_period: Literal["minutes", "hours", "days"] | None | Unset = Unset,
        start_time: datetime | None | Unset = Unset,
        enabled: bool | Unset = Unset,
        mappings: list[dict] | Unset = Unset,
    ) -> EtlTask:
        """
        Update an ETL task.
        """

        task = self.get(task=task, action="edit", principal=principal)

        editable_fields = {
            "name": name,
            "description": description,
            "runtime_variables": runtime_variables
        }

        for field, value in editable_fields.items():
            if value is not Unset:
                setattr(task, field, value)

        task.save()

        if any(field is not Unset for field in [crontab, interval, interval_period, start_time, enabled]):
            self.apply_schedule(
                task=task,
                crontab=crontab,
                interval=interval,
                interval_period=interval_period,
                start_time=start_time,
                enabled=enabled,
                celery_task_name="processing.etl.tasks.run_etl_task",
            )

        if mappings is not Unset:
            self.apply_mappings(task=task, mappings=mappings)

        return self.get(task.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def apply_mappings(
        self,
        task: Union[uuid.UUID, EtlTask],
        mappings: list[dict],
    ) -> None:
        """
        Replace the mappings on an ETL task, preserving existing ones that match.
        """

        task = self.get(task)

        new_mappings = {(m["source_identifier"], m["target_datastream"]) for m in mappings}
        current_mappings = {
            (m.source_identifier, m.target_datastream_id): m
            for m in task.etl_mappings.all()
        }

        task.etl_mappings.filter(
            pk__in=[m.pk for key, m in current_mappings.items() if key not in new_mappings]
        ).delete()

        for source_identifier, target_datastream in new_mappings:
            if (source_identifier, target_datastream) not in current_mappings:
                EtlMapping.objects.create(
                    etl_task=task,
                    source_identifier=source_identifier,
                    target_datastream_id=target_datastream,
                )

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def run(
        self,
        task: Union[uuid.UUID, EtlTask],
        principal: User | APIKey | None | Unset = Unset,
    ):
        """
        Build and run an ETL Pipeline.
        """

        task: EtlTask = self.get(task, action="edit", principal=principal)
        data_connection = task.data_connection
        etl_mappings = task.etl_mappings.all()

        extractor = HTTPExtractor(
            source_uri=data_connection.source_url
        )

        timestamp = Timestamp(
            timestamp_type="custom" if data_connection.timestamp_format is not None else "iso",
            timestamp_format=data_connection.timestamp_format,
            timezone_type=data_connection.timezone_type,  # noqa
            timezone=data_connection.timezone,
        )

        transformer_timestamp_settings = {
            "timestamp_key": data_connection.timestamp_key,
            "timestamp_format": data_connection.timestamp_format,
            "timezone_type": data_connection.timezone_type,
            "timezone": data_connection.timezone,
        }

        if data_connection.payload.payload_type == "CSV":
            transformer = CSVTransformer(
                **timestamp.model_dump(),
                timestamp_key=data_connection.timestamp_key,
                header_row=data_connection.payload.header_row,
                data_start_row=data_connection.payload.data_start_row,
                delimiter=data_connection.payload.delimiter,  # noqa
            )

        elif data_connection.payload.payload_type == "JSON":
            transformer = JSONTransformer(
                **transformer_timestamp_settings,
                jmespath=data_connection.payload.jmespath
            )

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

        context = etl_pipeline.run(
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
            **{
                pv.name: (
                    execution_time if pv.variable_type == "run_time" else
                    earliest_loaded_through if pv.variable_type == "latest_observation_timestamp" else
                    task.runtime_variables.get(pv.name)
                ) for pv in data_connection.placeholder_variables.all()
                if pv.variable_type in ("run_time", "latest_observation_timestamp", "per_task")
            },
        )

        if context.results.values_loaded_total == 0:
            message = "Already up-to-date. No new observations were loaded."
        else:
            message = (
                f"Loaded {context.results.values_loaded_total} total observation(s) "
                f"into {context.results.success_count} datastream(s)."
            )

        return {
            "message": message,
            "results": context.results.model_dump()
        }
