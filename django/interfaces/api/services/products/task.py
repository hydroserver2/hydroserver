import uuid
import logging
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
from processing.orchestration.services import TaskService
from processing.products.models import DataProductTask


User = get_user_model()

CELERY_TASK_NAME = "processing.products.tasks.run_data_product_task"

logger = logging.getLogger(__name__)


class DataProductTaskAPIService(TaskService[DataProductTask], APIService):

    task_model = DataProductTask

    order_by_fields = {
        "id", "name", "monitoring_site_id", "monitoring_site__name",
        "monitoring_site__workspace_id", "monitoring_site__workspace__name",
        "latest_run_status", "latest_run_started_at", "latest_run_finished_at",
    }

    def get(
        self,
        task: Union[uuid.UUID, DataProductTask],
        principal: User | ServiceAccount | AnonymousPrincipal | Unset = Unset,
        action: Literal["view", "edit", "delete"] = "view",
        expand_related: Optional[bool] = None,
    ) -> DataProductTask:
        """Get a data product task."""

        task = super().get(task=task, action=action, principal=principal)

        queryset = (
            self.annotate_latest_run(self.task_model.objects)
            .select_related("monitoring_site", "periodic_task__crontab", "periodic_task__interval")
        )

        if expand_related:
            queryset = queryset.select_related("monitoring_site__workspace").prefetch_related(
                "transformations__input_datastreams__datastream",
                "transformations__input_datastreams__datastream__datastream_linked_resources",
                "transformations__output_datastream",
                "transformations__output_datastream__datastream_linked_resources",
                "transformations__rating_curve",
            )
        else:
            queryset = queryset.prefetch_related("transformations__input_datastreams")

        return queryset.get(pk=task.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] = Field(default_factory=list),
        search_term: str | Unset = Unset,
        monitoring_site: list[uuid.UUID | MonitoringSite] | Unset = Unset,
        workspace: list[uuid.UUID | Workspace] | Unset = Unset,
        latest_run_status: list[str] | Unset = Unset,
        transformation_type: list[str] | Unset = Unset,
        output_datastream: list[uuid.UUID] | Unset = Unset,
        input_datastream: list[uuid.UUID] | Unset = Unset,
        rating_curve: list[uuid.UUID] | Unset = Unset,
        expand_related: Optional[bool] = None,
    ) -> tuple[int, list[DataProductTask]]:
        """Return a collection of data product tasks."""

        queryset = self.task_model.objects

        if latest_run_status is not Unset or any(
            term.lstrip("-") in self.latest_run_filter_fields for term in order_by
        ):
            queryset = self.annotate_latest_run(queryset, fields=self.latest_run_filter_fields)

        if search_term is not Unset:
            search_vector = SearchVector("name", "description", "monitoring_site__name")
            queryset = queryset.annotate(search=search_vector).filter(search=SearchQuery(search_term))

        if monitoring_site is not Unset:
            queryset = queryset.filter(monitoring_site__in=[getattr(t, "pk", t) for t in monitoring_site])

        if workspace is not Unset:
            queryset = queryset.filter(monitoring_site__workspace__in=[getattr(ws, "pk", ws) for ws in workspace])

        if latest_run_status is not Unset:
            queryset = queryset.filter(latest_run_status__in=latest_run_status)

        if transformation_type is not Unset:
            queryset = queryset.filter(transformations__transformation_type__in=transformation_type)

        if output_datastream is not Unset:
            queryset = queryset.filter(transformations__output_datastream__in=output_datastream)

        if input_datastream is not Unset:
            queryset = queryset.filter(transformations__input_datastreams__datastream__in=input_datastream)

        if rating_curve is not Unset:
            queryset = queryset.filter(transformations__rating_curve__in=rating_curve)

        if not all(term.lstrip("-") in self.order_by_fields for term in order_by):
            raise BadRequestError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "-id")

        if expand_related:
            queryset = queryset.select_related(
                "monitoring_site__workspace", "periodic_task__crontab", "periodic_task__interval"
            ).prefetch_related(
                "transformations__input_datastreams__datastream",
                "transformations__input_datastreams__datastream__datastream_linked_resources",
                "transformations__output_datastream",
                "transformations__output_datastream__datastream_linked_resources",
                "transformations__rating_curve",
            )
        else:
            queryset = queryset.select_related(
                "monitoring_site", "periodic_task__crontab", "periodic_task__interval"
            ).prefetch_related("transformations__input_datastreams")

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        count = queryset.count()
        offset = (page - 1) * page_size
        tasks = self.attach_latest_runs(list(queryset[offset:offset + page_size]))

        return count, tasks

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        monitoring_site: uuid.UUID | MonitoringSite,
        name: str,
        description: str | None = None,
        crontab: str | None = None,
        interval: int | None = None,
        interval_period: Literal["minutes", "hours", "days"] | None = None,
        start_time: datetime | None = None,
        enabled: bool = True,
        uid: uuid.UUID = Field(default_factory=uuid.uuid7),
    ) -> DataProductTask:
        """Create a data product task."""

        if isinstance(monitoring_site, uuid.UUID):
            try:
                monitoring_site = MonitoringSite.objects.select_related("workspace").get(pk=monitoring_site)
            except MonitoringSite.DoesNotExist:
                raise NotFoundError("MonitoringSite does not exist.")

        if not principal.can_create("DataProductTask", workspace=monitoring_site.workspace):
            raise PermissionDeniedError("You do not have permission to create this task.")

        task = self.task_model.objects.create(
            pk=uid,
            name=name,
            description=description,
            monitoring_site=monitoring_site,
        )

        self.apply_schedule(
            task=task,
            crontab=crontab,
            interval=interval,
            interval_period=interval_period,
            start_time=start_time,
            enabled=enabled,
            celery_task_name=CELERY_TASK_NAME,
        )

        return self.get(task.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        task: Union[uuid.UUID, DataProductTask],
        principal: User | ServiceAccount | AnonymousPrincipal,
        name: str | Unset = Unset,
        description: str | None | Unset = Unset,
        crontab: str | None | Unset = Unset,
        interval: int | None | Unset = Unset,
        interval_period: Literal["minutes", "hours", "days"] | None | Unset = Unset,
        start_time: datetime | None | Unset = Unset,
        enabled: bool | Unset = Unset,
    ) -> DataProductTask:
        """Update a data product task."""

        task = self.get(task=task, action="edit", principal=principal)

        editable_fields = {"name": name, "description": description}
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
                celery_task_name=CELERY_TASK_NAME,
            )

        return self.get(task.pk)
