import uuid
from datetime import datetime
from typing import Optional, Union, Literal

from pydantic import Field, ConfigDict, validate_call
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector, SearchQuery

from core.types import Unset
from core.iam.models import ServiceAccount, Workspace
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import BadRequestError, PermissionDeniedError, NotFoundError
from interfaces.api.service import APIService
from core.sta.models import MonitoringSite
from interfaces.api.services.sta.datastream import DatastreamAPIService
from processing.orchestration.services import TaskService
from processing.etl.models import EtlTask, EtlMapping, DataConnection


User = get_user_model()

datastream_service = DatastreamAPIService()


class EtlTaskAPIService(TaskService[EtlTask], APIService):

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
        principal: User | ServiceAccount | AnonymousPrincipal | Unset = Unset,
        expand_related: Optional[bool] = None,
    ) -> EtlTask:
        """Get an ETL task with related data and the latest run annotations."""

        task = super().get(task=task, action=action, principal=principal)

        queryset = (
            self.annotate_latest_run(self.task_model.objects)
            .select_related("data_connection", "periodic_task__crontab", "periodic_task__interval")
        )

        if expand_related:
            queryset = queryset.select_related(
                "data_connection__workspace", "periodic_task__crontab", "periodic_task__interval"
            ).prefetch_related(
                "etl_mappings", "etl_mappings__target_datastream",
                "etl_mappings__target_datastream__datastream_linked_resources"
            )

        return queryset.get(pk=task.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] | Unset = Unset,
        search_term: str | Unset = Unset,
        monitoring_site: list[uuid.UUID | MonitoringSite] | Unset = Unset,
        workspace: list[uuid.UUID | Workspace] | Unset = Unset,
        data_connection: list[uuid.UUID | DataConnection] | Unset = Unset,
        latest_run_status: list[str] | Unset = Unset,
        latest_run_started_at_min: datetime | Unset = Unset,
        latest_run_started_at_max: datetime | Unset = Unset,
        latest_run_finished_at_min: datetime | Unset = Unset,
        latest_run_finished_at_max: datetime | Unset = Unset,
        expand_related: Optional[bool] = None,
    ) -> tuple[int, list[EtlTask]]:
        """
        Return a collection of ETL tasks.
        """

        queryset = self.task_model.objects

        if order_by is Unset:
            order_by = []

        latest_run_filtered = any(value is not Unset for value in [
            latest_run_status, latest_run_started_at_min, latest_run_started_at_max,
            latest_run_finished_at_min, latest_run_finished_at_max,
        ])
        if latest_run_filtered or any(
            term.lstrip("-") in self.latest_run_filter_fields for term in order_by
        ):
            queryset = self.annotate_latest_run(queryset, fields=self.latest_run_filter_fields)

        if search_term is not Unset:
            search_vector = SearchVector("name", "description", "data_connection__name")
            queryset = queryset.annotate(search=search_vector).filter(search=SearchQuery(search_term))

        if monitoring_site is not Unset:
            queryset = queryset.filter(etl_mappings__target_datastream__monitoring_site__in=[
                getattr(t, "pk", t) for t in monitoring_site
            ])

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
            raise BadRequestError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "-id")

        if expand_related:
            queryset = queryset.select_related(
                "data_connection__workspace", "periodic_task__crontab", "periodic_task__interval"
            ).prefetch_related(
                "etl_mappings", "etl_mappings__target_datastream",
                "etl_mappings__target_datastream__datastream_linked_resources"
            )
        else:
            queryset = queryset.select_related(
                "data_connection", "periodic_task__crontab", "periodic_task__interval"
            )

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        count = queryset.count()
        offset = (page - 1) * page_size

        tasks = self.attach_latest_runs(list(queryset[offset:offset + page_size]))

        if expand_related:
            self._attach_data_connections(tasks)

        return count, tasks

    @staticmethod
    def _attach_data_connections(tasks: list[EtlTask]) -> list[EtlTask]:
        """
        Attach fully-resolved data connections to a page of tasks.

        Every ``EtlTaskResponse`` embeds a ``DataConnectionResponse`` whose resolvers (task
        counts, notification, schedule, recipients) would otherwise issue several queries *per
        task*. Because a task list is typically scoped to one data connection, we load the few
        distinct connections once -- with task counts annotated and notification data prefetched --
        and share them across the tasks, turning ~4 queries per row into a small constant.
        """

        from interfaces.api.services.etl.data_connection import DataConnectionAPIService

        connection_ids = {task.data_connection_id for task in tasks if task.data_connection_id}
        if not connection_ids:
            return tasks

        connections = DataConnectionAPIService.annotate_task_counts(
            DataConnection.objects
            .filter(pk__in=connection_ids)
            .select_related(
                "workspace",
                "notification__periodic_task__crontab",
                "notification__periodic_task__interval",
            )
            .prefetch_related(
                "placeholder_variables",
                "payload",
                "notification__recipients",
            )
        )
        connections_by_id = {connection.pk: connection for connection in connections}

        for task in tasks:
            connection = connections_by_id.get(task.data_connection_id)
            if connection is not None:
                task.data_connection = connection

        return tasks

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        name: str,
        data_connection: Union[uuid.UUID, DataConnection],
        uid: uuid.UUID = Field(default_factory=uuid.uuid7),
        description: str | None = None,
        task_variables: dict | None = None,
        crontab: str | None = None,
        interval: int | None = None,
        interval_period: Literal["minutes", "hours", "days"] | None = None,
        start_time: datetime | None = None,
        enabled: bool = True,
        mappings: list[dict] | None = None,
    ) -> EtlTask:
        """
        Create an ETL task.
        """

        if task_variables is None:
            task_variables = {}

        if mappings is None:
            mappings = []

        if isinstance(data_connection, uuid.UUID):
            try:
                data_connection = DataConnection.objects.get(pk=data_connection)
            except DataConnection.DoesNotExist:
                raise NotFoundError(f"Data connection with ID {str(data_connection)} does not exist.")

        if not principal.can_create("EtlTask", workspace=data_connection.workspace):
            raise PermissionDeniedError("You do not have permission to create this task.")

        task = self.task_model.objects.create(
            pk=uid,
            name=name,
            description=description,
            data_connection=data_connection,
            task_variables=task_variables,
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

        self.apply_mappings(task=task, mappings=mappings, principal=principal)

        return self.get(task.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        task: Union[uuid.UUID, EtlTask],
        principal: User | ServiceAccount | AnonymousPrincipal,
        name: str | Unset = Unset,
        description: str | None | Unset = Unset,
        task_variables: dict | Unset = Unset,
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
            "task_variables": task_variables
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
            self.apply_mappings(task=task, mappings=mappings, principal=principal)

        return self.get(task.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def apply_mappings(
        self,
        task: Union[uuid.UUID, EtlTask],
        mappings: list[dict],
        principal: User | ServiceAccount | AnonymousPrincipal,
    ) -> None:
        """
        Replace the mappings on an ETL task, preserving existing ones that match.
        """

        task = self.get(task)

        target_ids = [m["target_datastream"] for m in mappings]

        for target_id in target_ids:
            datastream_service.get_datastream_for_action(
                principal=principal, uid=target_id, action="edit"
            )

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
                new_mapping = EtlMapping(
                    etl_task=task,
                    source_identifier=source_identifier,
                    target_datastream_id=target_datastream,
                )
                new_mapping.full_clean()
                new_mapping.save()
