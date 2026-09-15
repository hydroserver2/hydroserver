import uuid
import logging

from typing import Optional, Literal, get_args
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector, SearchQuery

from core.types import Unset
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import MonitoringSite
from processing.orchestration.services import TaskService
from processing.products.models import DataProductTask, DataProductTransformation
from interfaces.api.http.errors import PermissionDeniedError, NotFoundError
from interfaces.api.service import APIService
from interfaces.api.schemas.products.task import (
    DataProductTaskSortByFields,
    DataProductTaskResponse,
    DataProductTaskPostBody,
    DataProductTaskPatchBody,
    DATA_PRODUCT_TASK_INCLUDE_RELATIONS,
)


User = get_user_model()

CELERY_TASK_NAME = "processing.products.tasks.run_data_product_task"

logger = logging.getLogger(__name__)


class DataProductTaskAPIService(TaskService[DataProductTask], APIService):

    task_model = DataProductTask
    INCLUDE_RELATIONS = DATA_PRODUCT_TASK_INCLUDE_RELATIONS

    sortby_aliases = {
        "monitoringSiteName": "monitoring_site__name",
        "workspaceId": "monitoring_site__workspace_id",
        "workspaceName": "monitoring_site__workspace__name",
    }

    @classmethod
    def _include_query_hints(cls, requested_includes: set[str]) -> tuple[list[str], list[str]]:
        select_paths = [cls.INCLUDE_RELATIONS[name]["path"] for name in requested_includes]
        prefetch_paths = []
        if "monitoringSite" in requested_includes:
            prefetch_paths.append("monitoring_site__monitoring_site_linked_resources")

        return select_paths, prefetch_paths

    def get_task_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"] = "view",
    ) -> DataProductTask:
        return self.get(task=uid, action=action, principal=principal)

    def get(
        self,
        task: uuid.UUID | DataProductTask,
        action: Literal["view", "edit", "delete"] = "view",
        principal: User | ServiceAccount | AnonymousPrincipal | Unset = Unset,
        include: Optional[list[str]] = None,
    ) -> DataProductTask:
        requested_includes = self.resolve_include_set(include)
        task = super().get(task=task, action=action, principal=principal)

        queryset = self.annotate_latest_run(self.task_model.objects).select_related(
            "periodic_task__crontab", "periodic_task__interval"
        )
        if requested_includes:
            select_paths, prefetch_paths = self._include_query_hints(requested_includes)
            queryset = queryset.select_related(*select_paths)
            if prefetch_paths:
                queryset = queryset.prefetch_related(*prefetch_paths)

        task = queryset.get(pk=task.pk)
        self.attach_transformation_types([task])

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
            "data": DataProductTaskResponse.model_validate(task),
            "included": self.resolve_includes(
                [task], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    @staticmethod
    def attach_transformation_types(tasks: list[DataProductTask]) -> list[DataProductTask]:
        task_ids = [task.pk for task in tasks]
        grouped: dict[uuid.UUID, list[str]] = {}

        if task_ids:
            for task_id, transformation_type in (
                DataProductTransformation.objects
                .filter(task_id__in=task_ids)
                .values_list("task_id", "transformation_type")
            ):
                grouped.setdefault(task_id, []).append(transformation_type)

        for task in tasks:
            task.transformation_types = grouped.get(task.pk, [])

        return tasks

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        sortby: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        filtering = filtering or {}

        queryset = self.task_model.objects

        sortby = sortby or []

        if "latest_run_status" in filtering or any(
            term.lstrip("-") in self.latest_run_filter_fields for term in sortby
        ):
            queryset = self.annotate_latest_run(queryset, fields=self.latest_run_filter_fields)

        if "search_term" in filtering:
            search_vector = SearchVector("name", "description", "monitoring_site__name")
            queryset = queryset.annotate(search=search_vector).filter(
                search=SearchQuery(filtering["search_term"])
            )

        if "monitoring_site" in filtering:
            queryset = self.apply_filters(queryset, "monitoring_site_id", filtering["monitoring_site"])

        if "workspace" in filtering:
            queryset = self.apply_filters(
                queryset, "monitoring_site__workspace_id", filtering["workspace"]
            )

        if "latest_run_status" in filtering:
            queryset = self.apply_filters(queryset, "latest_run_status", filtering["latest_run_status"])

        if "transformation_type" in filtering:
            queryset = self.apply_filters(
                queryset, "transformations__transformation_type", filtering["transformation_type"]
            )

        if "output_datastream" in filtering:
            queryset = self.apply_filters(
                queryset, "transformations__output_datastream", filtering["output_datastream"]
            )

        if "input_datastream" in filtering:
            queryset = self.apply_filters(
                queryset,
                "transformations__input_datastreams__datastream",
                filtering["input_datastream"],
            )

        if "rating_curve" in filtering:
            queryset = self.apply_filters(
                queryset, "transformations__rating_curve", filtering["rating_curve"]
            )

        queryset = self.apply_sorting(
            queryset, sortby, list(get_args(DataProductTaskSortByFields)), self.sortby_aliases
        )

        queryset = queryset.select_related(
            "periodic_task__crontab", "periodic_task__interval"
        )

        if requested_includes:
            select_paths, prefetch_paths = self._include_query_hints(requested_includes)
            queryset = queryset.select_related(*select_paths)
            if prefetch_paths:
                queryset = queryset.prefetch_related(*prefetch_paths)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()
        queryset, meta = self.apply_pagination(queryset, offset, limit)
        tasks = self.attach_latest_runs(list(queryset.all()))

        self.attach_transformation_types(tasks)

        return {
            "data": [DataProductTaskResponse.model_validate(task) for task in tasks],
            "meta": meta,
            "included": self.resolve_includes(
                tasks, requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: DataProductTaskPostBody,
    ):
        try:
            monitoring_site = MonitoringSite.objects.select_related("workspace").get(
                pk=data.monitoring_site_id
            )
        except MonitoringSite.DoesNotExist:
            raise NotFoundError("MonitoringSite does not exist.")

        if not principal.can_create("DataProductTask", workspace=monitoring_site.workspace):
            raise PermissionDeniedError("You do not have permission to create this task.")

        task = self.task_model.objects.create(
            pk=data.uid if data.uid is not Unset else uuid.uuid7(),
            name=data.name,
            description=data.description,
            monitoring_site=monitoring_site,
        )

        schedule = data.schedule
        self.apply_schedule(
            task=task,
            crontab=schedule.crontab if schedule else None,
            interval=schedule.interval if schedule else None,
            interval_period=schedule.interval_period if schedule else None,
            start_time=schedule.start_time if schedule else None,
            enabled=schedule.enabled if schedule else True,
            celery_task_name=CELERY_TASK_NAME,
        )

        return {"id": task.pk}

    @transaction.atomic
    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: DataProductTaskPatchBody,
    ):
        task = self.get_task_for_action(principal=principal, uid=uid, action="edit")

        task_data = data.dict(
            include=set(DataProductTaskPatchBody.model_fields.keys()) - {"schedule"},
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
                celery_task_name=CELERY_TASK_NAME,
            )
