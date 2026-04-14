import uuid
import uuid6
from datetime import datetime
from typing import Optional, Union, Literal

from pydantic import Field, ConfigDict, validate_call
from ninja.errors import HttpError
from django.db import transaction
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector, SearchQuery

from core.types import Unset
from core.iam.models import APIKey, Workspace
from core.service import ServiceUtils
from core.sta.models import Thing
from processing.orchestration.services import TaskService
from processing.monitoring.models import MonitoringTask, MonitoringNotificationRecipient


User = get_user_model()

CELERY_TASK_NAME = "processing.monitoring.tasks.run_monitoring_task"


class MonitoringTaskService(TaskService[MonitoringTask], ServiceUtils):

    task_model = MonitoringTask

    order_by_fields = {
        "id", "name", "thing_id", "thing__name",
        "thing__workspace_id", "thing__workspace__name",
        "latest_run_status", "latest_run_started_at", "latest_run_finished_at",
    }

    def get(
        self,
        task: Union[uuid.UUID, MonitoringTask],
        action: Literal["view", "edit", "delete"] = "view",
        principal: User | APIKey | None | Unset = Unset,
    ) -> MonitoringTask:
        """
        Get a monitoring task.
        """

        task = super().get(task=task, action=action, principal=principal)

        if isinstance(task.pk, uuid.UUID):
            task = (
                self.annotate_latest_run(self.task_model.objects)
                .select_related("thing__workspace", "periodic_task__crontab", "periodic_task__interval")
                .prefetch_related("rules__datastream", "recipients")
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
        thing: list[uuid.UUID | Thing] | Unset = Unset,
        workspace: list[uuid.UUID | Workspace] | Unset = Unset,
        latest_run_status: list[str] | Unset = Unset,
        datastream: list[uuid.UUID] | Unset = Unset,
        rule_type: list[str] | Unset = Unset,
    ) -> tuple[int, QuerySet[MonitoringTask]]:
        """
        Return a collection of monitoring tasks.
        """

        queryset = self.task_model.objects
        queryset = self.annotate_latest_run(queryset)

        if search_term is not Unset:
            search_vector = SearchVector("name", "description", "thing__name")
            queryset = queryset.annotate(search=search_vector).filter(search=SearchQuery(search_term))

        if thing is not Unset:
            queryset = queryset.filter(thing__in=[getattr(t, "pk", t) for t in thing])

        if workspace is not Unset:
            queryset = queryset.filter(thing__workspace__in=[getattr(w, "pk", w) for w in workspace])

        if latest_run_status is not Unset:
            queryset = queryset.filter(latest_run_status__in=latest_run_status)

        if datastream is not Unset:
            queryset = queryset.filter(rules__datastream__in=datastream)

        if rule_type is not Unset:
            queryset = queryset.filter(rules__rule_type__in=rule_type)

        if not all(term.lstrip("-") in self.order_by_fields for term in order_by):
            raise ValueError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "-id")
        queryset = queryset.select_related(
            "thing__workspace", "periodic_task__crontab", "periodic_task__interval"
        ).prefetch_related("rules__datastream", "recipients")
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
        thing: uuid.UUID | Thing,
        name: str,
        uid: uuid.UUID = Field(default_factory=uuid6.uuid7),
        description: str | None = None,
        recipients: list[str] = Field(default_factory=list),
        crontab: str | None = None,
        interval: int | None = None,
        interval_period: Literal["minutes", "hours", "days"] | None = None,
        start_time: datetime | None = None,
        enabled: bool = True,
    ) -> MonitoringTask:
        """
        Create a monitoring task.
        """

        if isinstance(thing, uuid.UUID):
            try:
                thing = Thing.objects.select_related("workspace").get(pk=thing)
            except Thing.DoesNotExist:
                raise HttpError(404, "Thing does not exist.")

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

        self.apply_recipients(task=task, emails=recipients)

        return self.get(task.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        task: Union[uuid.UUID, MonitoringTask],
        principal: User | APIKey,
        name: str | Unset = Unset,
        description: str | None | Unset = Unset,
        recipients: list[str] | Unset = Unset,
        crontab: str | None | Unset = Unset,
        interval: int | None | Unset = Unset,
        interval_period: Literal["minutes", "hours", "days"] | None | Unset = Unset,
        start_time: datetime | None | Unset = Unset,
        enabled: bool | Unset = Unset,
    ) -> MonitoringTask:
        """
        Update a monitoring task.
        """

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

        if recipients is not Unset:
            self.apply_recipients(task=task, emails=recipients)

        return self.get(task.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def apply_recipients(
        self,
        task: Union[uuid.UUID, MonitoringTask],
        emails: list[str],
    ) -> None:
        """Replace all notification recipients on a task."""

        task = super().get(task)

        task.recipients.all().delete()

        MonitoringNotificationRecipient.objects.bulk_create([
            MonitoringNotificationRecipient(task=task, email=email)
            for email in set(emails)
        ])

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def run(
        self,
        task: Union[uuid.UUID, MonitoringTask],
        principal: User | APIKey | None | Unset = Unset,
    ):
        """
        Run a monitoring task.
        """
