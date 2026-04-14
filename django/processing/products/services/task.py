import uuid
import uuid6
import logging
from datetime import datetime
from typing import Union, Literal

from pydantic import Field, ConfigDict, validate_call
from django.db import transaction
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector, SearchQuery

from core.types import Unset
from core.iam.models import APIKey, Workspace
from core.service import ServiceUtils
from core.sta.models import Thing
from processing.orchestration.services import TaskService
from processing.products.models import DataProductTask
from processing.products.services.transformation import DataProductTransformationService


User = get_user_model()

CELERY_TASK_NAME = "processing.products.tasks.run_data_product_task"

logger = logging.getLogger(__name__)

transformation_service = DataProductTransformationService()


class DataProductTaskService(TaskService[DataProductTask], ServiceUtils):

    task_model = DataProductTask

    order_by_fields = {
        "id", "name", "thing_id", "thing__name",
        "thing__workspace_id", "thing__workspace__name",
        "latest_run_status", "latest_run_started_at", "latest_run_finished_at",
    }

    def get(
        self,
        task: Union[uuid.UUID, DataProductTask],
        principal: User | APIKey | None | Unset = Unset,
        action: Literal["view", "edit", "delete"] = "view",
    ) -> DataProductTask:
        """Get a data product task."""

        task = super().get(task=task, action=action, principal=principal)

        if isinstance(task.pk, uuid.UUID):
            task = (
                self.annotate_latest_run(self.task_model.objects)
                .select_related("thing__workspace", "periodic_task__crontab", "periodic_task__interval")
                .prefetch_related(
                    "transformations__input_datastreams__datastream",
                    "transformations__output_datastream",
                    "transformations__rating_curve",
                )
                .get(pk=task.pk)
            )

        return task

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        principal: User | APIKey | None | Unset = Unset,
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] = Field(default_factory=list),
        search_term: str | Unset = Unset,
        thing: list[uuid.UUID | Thing] | Unset = Unset,
        workspace: list[uuid.UUID | Workspace] | Unset = Unset,
        latest_run_status: list[str] | Unset = Unset,
        transformation_type: list[str] | Unset = Unset,
        output_datastream: list[uuid.UUID] | Unset = Unset,
        input_datastream: list[uuid.UUID] | Unset = Unset,
        rating_curve: list[uuid.UUID] | Unset = Unset,
    ) -> tuple[int, QuerySet[DataProductTask]]:
        """Return a collection of data product tasks."""

        queryset = self.task_model.objects
        queryset = self.annotate_latest_run(queryset)

        if search_term is not Unset:
            search_vector = SearchVector("name", "description", "thing__name")
            queryset = queryset.annotate(search=search_vector).filter(search=SearchQuery(search_term))

        if thing is not Unset:
            queryset = queryset.filter(thing__in=[getattr(t, "pk", t) for t in thing])

        if workspace is not Unset:
            queryset = queryset.filter(thing__workspace__in=[getattr(ws, "pk", ws) for ws in workspace])

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
            raise ValueError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "-id")
        queryset = queryset.select_related(
            "thing__workspace", "periodic_task__crontab", "periodic_task__interval"
        ).prefetch_related(
            "transformations__input_datastreams__datastream",
            "transformations__output_datastream",
            "transformations__rating_curve",
        )
        queryset = queryset.visible(principal=principal).distinct()  # noqa

        count = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]

        return count, queryset

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | APIKey | None,
        thing: uuid.UUID | Thing,
        name: str,
        description: str | None = None,
        crontab: str | None = None,
        interval: int | None = None,
        interval_period: Literal["minutes", "hours", "days"] | None = None,
        start_time: datetime | None = None,
        enabled: bool = True,
        uid: uuid.UUID = Field(default_factory=uuid6.uuid7),
    ) -> DataProductTask:
        """Create a data product task."""

        if isinstance(thing, uuid.UUID):
            try:
                thing = Thing.objects.select_related("workspace").get(pk=thing)
            except Thing.DoesNotExist:
                raise LookupError("Thing does not exist.")

        if not self.task_model.can_principal_create(principal=principal, workspace=thing.workspace):
            raise PermissionError("You do not have permission to create this task.")

        task = self.task_model.objects.create(
            pk=uid,
            name=name,
            description=description,
            thing=thing,
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
        principal: User | APIKey | None,
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

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def run(
        self,
        task: Union[uuid.UUID, DataProductTask],
        principal: User | APIKey | None | Unset = Unset,
    ) -> dict:
        """Run all transformations for this task."""

        task = self.get(task=task, action="edit", principal=principal)

        transformations = list(
            task.transformations
            .select_related("output_datastream", "rating_curve", "task__thing__workspace")
            .prefetch_related("input_datastreams__datastream", "rating_curve__points")
        )

        loaded_total = 0
        success_count = 0

        for transformation in transformations:
            try:
                loaded = transformation_service.run(transformation)
                loaded_total += loaded
                success_count += 1
            except (Exception,):
                logger.error(
                    "Failed to run transformation %s (%s → %s)",
                    transformation.id,
                    transformation.transformation_type,
                    transformation.output_datastream_id,
                    exc_info=True,
                )

        total = len(transformations)

        if loaded_total == 0:
            message = "Already up-to-date. No new observations were loaded."
        else:
            message = (
                f"Loaded {loaded_total} observation(s) across "
                f"{success_count} of {total} transformation(s)."
            )

        return {"message": message, "loaded_total": loaded_total}
