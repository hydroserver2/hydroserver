import uuid
from typing import Optional, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from domains.iam.models import APIKey
from domains.etl.models import TaskRun
from interfaces.api.schemas import TaskRunFields, TaskRunPostBody, TaskRunPatchBody, TaskRunOrderByFields
from interfaces.api.service import ServiceUtils
from .task import TaskService

User = get_user_model()

task_service = TaskService()


class TaskRunService(ServiceUtils):
    def list(
        self,
        principal: Optional[User | APIKey],
        response: HttpResponse,
        task_id: uuid.UUID,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
    ):
        task = task_service.get_task_for_action(
            principal=principal, uid=task_id, action="view", expand_related=True
        )

        queryset = TaskRun.objects.filter(task=task)

        for field in [
            "status",
            "started_at__lte",
            "started_at__gte",
            "finished_at__lte",
            "finished_at__gte",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(TaskRunOrderByFields)),
            )
        else:
            queryset = queryset.order_by("id")

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset

    @staticmethod
    def get(
        principal: User | APIKey,
        uid: uuid.UUID,
        task_id: uuid.UUID,
    ):
        task = task_service.get_task_for_action(
            principal=principal, uid=task_id, action="view", expand_related=True
        )

        try:
            task_run = TaskRun.objects.get(pk=uid, task=task)
        except TaskRun.DoesNotExist:
            raise HttpError(404, "Task run not found")

        return task_run

    def create(
        self,
        principal: User | APIKey,
        task_id: uuid.UUID,
        data: TaskRunPostBody,
    ):
        task = task_service.get_task_for_action(
            principal=principal, uid=task_id, action="edit", expand_related=True
        )

        task_run_data = data.dict(include=set(TaskRunFields.model_fields.keys()))

        try:
            task_run = TaskRun.objects.create(
                pk=data.id,
                task=task,
                **task_run_data,
            )
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        return self.get(
            principal=principal,
            uid=task_run.id,
            task_id=task_id,
        )

    def update(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        task_id: uuid.UUID,
        data: TaskRunPatchBody,
    ):
        task = task_service.get_task_for_action(
            principal=principal, uid=task_id, action="edit", expand_related=True
        )

        try:
            task_run = TaskRun.objects.get(pk=uid, task=task)
        except TaskRun.DoesNotExist:
            raise HttpError(404, "Task run not found")

        task_run_data = data.dict(
            include=set(TaskRunFields.model_fields.keys()),
            exclude_unset=True,
        )

        for field, value in task_run_data.items():
            setattr(task_run, field, value)

        task_run.save()

        return self.get(
            principal=principal, uid=task_run.id, task_id=task_id
        )

    @staticmethod
    def delete(principal: User | APIKey, uid: uuid.UUID, task_id: uuid.UUID):
        task = task_service.get_task_for_action(
            principal=principal, uid=task_id, action="edit", expand_related=True
        )

        try:
            task_run = TaskRun.objects.get(pk=uid, task=task)
        except TaskRun.DoesNotExist:
            raise HttpError(404, "Task run not found")

        task_run.delete()

        return "ETL task run deleted"
