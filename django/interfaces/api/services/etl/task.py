import uuid
from typing import Optional, Literal, get_args

from django.db import transaction
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector, SearchQuery

from core.types import Unset
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import PermissionDeniedError, NotFoundError
from interfaces.api.service import APIService
from processing.orchestration.services import TaskService
from processing.etl.models import EtlTask, DataConnection
from interfaces.api.schemas.etl.task import (
    EtlTaskSortByFields,
    EtlTaskResponse,
    EtlTaskPostBody,
    EtlTaskPatchBody,
    ETL_TASK_INCLUDE_RELATIONS,
)


User = get_user_model()


class EtlTaskAPIService(TaskService[EtlTask], APIService):

    task_model = EtlTask
    INCLUDE_RELATIONS = ETL_TASK_INCLUDE_RELATIONS

    sortby_aliases = {
        "dataConnectionName": "data_connection__name",
        "workspaceId": "data_connection__workspace_id",
        "workspaceName": "data_connection__workspace__name",
    }

    def get_task_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"] = "view",
    ) -> EtlTask:
        return self.get(task=uid, action=action, principal=principal)

    def get(
        self,
        task: uuid.UUID | EtlTask,
        action: Literal["view", "edit", "delete"] = "view",
        principal: User | ServiceAccount | AnonymousPrincipal | Unset = Unset,
        include: Optional[list[str]] = None,
    ) -> EtlTask:
        requested_includes = self.resolve_include_set(include)
        task = super().get(task=task, action=action, principal=principal)

        queryset = (
            self.annotate_latest_run(self.task_model.objects)
            .annotate(mapping_count=Count("etl_mappings", distinct=True))
            .select_related("periodic_task__crontab", "periodic_task__interval")
        )
        task = queryset.get(pk=task.pk)

        if "dataConnection" in requested_includes:
            self._attach_data_connections([task])

        return task

    def get_item(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        task = self.get(task=uid, action="view", principal=principal, include=include)

        return {
            "data": EtlTaskResponse.model_validate(task),
            "included": self.resolve_includes(
                [task], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        sortby: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
        properties: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        filtering = filtering or {}

        queryset = self.task_model.objects

        sortby = sortby or []

        latest_run_fields = [
            "latest_run_status", "latest_run_started_at_min", "latest_run_started_at_max",
            "latest_run_finished_at_min", "latest_run_finished_at_max",
        ]
        if any(field in filtering for field in latest_run_fields) or any(
            term.lstrip("-") in self.latest_run_filter_fields for term in sortby
        ):
            queryset = self.annotate_latest_run(queryset, fields=self.latest_run_filter_fields)

        if "search_term" in filtering:
            search_vector = SearchVector("name", "description", "data_connection__name")
            queryset = queryset.annotate(search=search_vector).filter(
                search=SearchQuery(filtering["search_term"])
            )

        if "monitoring_site_id" in filtering:
            queryset = self.apply_filters(
                queryset, "etl_mappings__target_datastream__monitoring_site_id", filtering["monitoring_site_id"]
            )

        if "workspace_id" in filtering:
            queryset = self.apply_filters(
                queryset, "data_connection__workspace_id", filtering["workspace_id"]
            )

        if "data_connection_id" in filtering:
            queryset = self.apply_filters(queryset, "data_connection_id", filtering["data_connection_id"])

        if "latest_run_status" in filtering:
            queryset = self.apply_filters(queryset, "latest_run_status", filtering["latest_run_status"])

        if "latest_run_started_at_min" in filtering:
            queryset = queryset.filter(latest_run_started_at__gte=filtering["latest_run_started_at_min"])

        if "latest_run_started_at_max" in filtering:
            queryset = queryset.filter(latest_run_started_at__lte=filtering["latest_run_started_at_max"])

        if "latest_run_finished_at_min" in filtering:
            queryset = queryset.filter(latest_run_finished_at__gte=filtering["latest_run_finished_at_min"])

        if "latest_run_finished_at_max" in filtering:
            queryset = queryset.filter(latest_run_finished_at__lte=filtering["latest_run_finished_at_max"])

        queryset = self.apply_sorting(
            queryset, sortby, list(get_args(EtlTaskSortByFields)), self.sortby_aliases
        )

        queryset = queryset.select_related("periodic_task__crontab", "periodic_task__interval")

        if properties is None or "mappingCount" in properties:
            queryset = queryset.annotate(mapping_count=Count("etl_mappings", distinct=True))

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        queryset, meta = self.apply_pagination(queryset, offset, limit)

        tasks = list(queryset.all())

        if properties is None or "latestRun" in properties:
            tasks = self.attach_latest_runs(tasks)

        if properties is not None and "mappingCount" not in properties:
            for task in tasks:
                task.mapping_count = 0

        if "dataConnection" in requested_includes:
            self._attach_data_connections(tasks)

        return {
            "data": [EtlTaskResponse.model_validate(task) for task in tasks],
            "meta": meta,
            "included": self.resolve_includes(
                tasks, requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    @staticmethod
    def _attach_data_connections(tasks: list[EtlTask]) -> list[EtlTask]:
        from interfaces.api.services.etl.data_connection import DataConnectionAPIService

        connection_ids = {task.data_connection_id for task in tasks if task.data_connection_id}
        if not connection_ids:
            return tasks

        connections = DataConnectionAPIService.annotate_task_counts(
            DataConnection.objects
            .filter(pk__in=connection_ids)
            .select_related(
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

    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: EtlTaskPostBody,
    ):
        try:
            data_connection = DataConnection.objects.select_related("workspace").get(
                pk=data.data_connection_id
            )
        except DataConnection.DoesNotExist:
            raise NotFoundError(f"Data connection with ID {data.data_connection_id} does not exist.")

        if not principal.can_create("EtlTask", workspace=data_connection.workspace):
            raise PermissionDeniedError("You do not have permission to create this task.")

        task = self.task_model.objects.create(
            pk=data.uid if data.uid is not Unset else uuid.uuid7(),
            name=data.name,
            description=data.description,
            data_connection=data_connection,
            task_variables=data.task_variables,
        )

        schedule = data.schedule
        self.apply_schedule(
            task=task,
            crontab=schedule.crontab if schedule else None,
            interval=schedule.interval if schedule else None,
            interval_period=schedule.interval_period if schedule else None,
            start_time=schedule.start_time if schedule else None,
            enabled=schedule.enabled if schedule else True,
            celery_task_name="processing.etl.tasks.run_etl_task",
        )

        return {"id": task.pk}

    @transaction.atomic
    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: EtlTaskPatchBody,
    ):
        task = self.get_task_for_action(principal=principal, uid=uid, action="edit")

        task_data = data.dict(
            include=set(EtlTaskPatchBody.model_fields.keys()) - {"schedule"},
            exclude_unset=True,
        )
        for field, value in task_data.items():
            setattr(task, field, value)

        task.save()

        if data.schedule is not Unset:
            schedule = data.schedule
            self.apply_schedule(
                task=task,
                crontab=schedule.crontab if schedule else None,
                interval=schedule.interval if schedule else None,
                interval_period=schedule.interval_period if schedule else None,
                start_time=schedule.start_time if schedule else None,
                enabled=schedule.enabled if schedule else True,
                celery_task_name="processing.etl.tasks.run_etl_task",
            )
