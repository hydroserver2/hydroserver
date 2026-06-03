import uuid
from datetime import datetime
from typing import Optional, Union, Literal, Generic, TypeVar
from pydantic import validate_call, ConfigDict, Field

from django.db import transaction
from django.db.models import QuerySet, Subquery, OuterRef
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector, SearchQuery

from core.types import Unset
from core.iam.models import APIKey
from processing.orchestration.models import Task, TaskRun
from processing.orchestration.services.scheduling import SchedulingService


User = get_user_model()

T = TypeVar("T", bound=Task)


class TaskService(SchedulingService, Generic[T]):

    task_model: type[T]
    task_run_order_by_fields = {"id", "started_at", "finished_at", "status"}

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        self,
        task: Union[uuid.UUID, T],
        action: Literal["view", "edit", "delete"] = "view",
        principal: User | APIKey | None | Unset = Unset,
    ) -> T:
        """Get a task."""

        if isinstance(task, uuid.UUID):
            try:
                task = self.task_model.objects.get(pk=task)
            except self.task_model.DoesNotExist:
                raise LookupError(f"Task with ID {str(task)} does not exist.")

        if principal is not Unset:
            permissions = task.get_principal_permissions(principal=principal)

            if "view" not in permissions:
                raise LookupError(f"Task with ID {str(task.id)} does not exist.")

            if action not in permissions:
                raise PermissionError(f"You do not have permission to {action} this task.")

        return task

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def delete(
        self,
        task: Union[uuid.UUID, T],
        principal: User | APIKey,
    ) -> None:
        """Delete a task."""

        task = self.get(task=task, action="delete", principal=principal)
        task.delete()

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def apply_schedule(
        self,
        task: Union[T, uuid.UUID],
        crontab: Union[Optional[str], Unset] = Unset,
        interval: Union[Optional[int], Unset] = Unset,
        interval_period: Union[Optional[Literal["minutes", "hours", "days"]], Unset] = Unset,
        start_time: Union[Optional[datetime], Unset] = Unset,
        enabled: Union[bool, Unset] = Unset,
        celery_task_name: Union[Optional[str], Unset] = Unset,
    ) -> T:
        """
        Update or create a schedule for a task.
        """

        task = self.get(task)

        task.periodic_task = super().apply_schedule(
            periodic_task=task.periodic_task,
            crontab=crontab,
            interval=interval,
            interval_period=interval_period,
            start_time=start_time,
            enabled=enabled,
            celery_task_name=celery_task_name,
            celery_task_kwargs={"task_id": str(task.id)},
            periodic_task_name=str(task.id),
        )

        task.next_run_at = SchedulingService.compute_next_run_at(task.periodic_task)

        task.save()

        return task

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_run(
        self,
        task: Union[T, uuid.UUID],
        run: uuid.UUID,
        principal: User | APIKey | None | Unset = Unset,
    ) -> TaskRun:
        """
        Return a single TaskRun by ID, scoped to the given task.
        """

        task = self.get(task=task, action="view", principal=principal)

        try:
            return TaskRun.objects.get(pk=run, task=task)
        except TaskRun.DoesNotExist:
            raise LookupError(f"TaskRun with ID {run} does not exist.")

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_run_collection(
        self,
        task: Union[T, uuid.UUID],
        principal: User | APIKey | None | Unset = Unset,
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] = Field(default_factory=list),
        search_term: str | Unset = Unset,
        status: list[str] | Unset = Unset,
        started_at__gte: datetime | Unset = Unset,
        started_at__lte: datetime | Unset = Unset,
        finished_at__gte: datetime | Unset = Unset,
        finished_at__lte: datetime | Unset = Unset,
    ) -> tuple[int, QuerySet[TaskRun]]:
        """
        Return a queryset of task runs for the given task.
        """

        task = self.get(task=task, action="view", principal=principal)

        queryset = TaskRun.objects.filter(task=task)

        if search_term is not Unset:
            search_vector = SearchVector("status", "message")
            queryset = queryset.annotate(search=search_vector).filter(search=SearchQuery(search_term))

        if status is not Unset:
            queryset = queryset.filter(status__in=status)

        if started_at__gte is not Unset:
            queryset = queryset.filter(started_at__gte=started_at__gte)

        if started_at__lte is not Unset:
            queryset = queryset.filter(started_at__lte=started_at__lte)

        if finished_at__gte is not Unset:
            queryset = queryset.filter(finished_at__gte=finished_at__gte)

        if finished_at__lte is not Unset:
            queryset = queryset.filter(finished_at__lte=finished_at__lte)

        if not all(term.lstrip("-") in self.task_run_order_by_fields for term in order_by):
            raise ValueError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "-started_at", "-id")

        count = queryset.count()
        offset = (page - 1) * page_size

        queryset = queryset[offset:offset + page_size]

        return count, queryset

    #: Latest-run fields that can be used to filter or order a task collection. These are the
    #: only annotations that have to be computed in the database before pagination.
    latest_run_filter_fields = {"latest_run_status", "latest_run_started_at", "latest_run_finished_at"}

    #: Mapping of latest-run annotation name -> TaskRun field it pulls from.
    latest_run_field_map = {
        "latest_run_id": "id",
        "latest_run_status": "status",
        "latest_run_started_at": "started_at",
        "latest_run_finished_at": "finished_at",
        "latest_run_message": "message",
        "latest_run_result": "result",
    }

    @classmethod
    def annotate_latest_run(cls, queryset: QuerySet, fields: set[str] | None = None) -> QuerySet:
        """
        Annotate a task queryset with fields from the latest run.

        Each annotation is a correlated subquery evaluated per row, so callers that only need a
        subset (e.g. for filtering or ordering) should pass ``fields`` to avoid computing the
        rest. See ``attach_latest_runs`` for resolving full latest-run data on a page of results
        without the per-row subqueries.
        """

        latest = TaskRun.objects.filter(task_id=OuterRef("pk")).order_by("-started_at", "-id")
        selected = cls.latest_run_field_map if fields is None else {
            name: source for name, source in cls.latest_run_field_map.items() if name in fields
        }
        annotations = {
            name: Subquery(latest.values(source)[:1]) for name, source in selected.items()
        }

        return queryset.annotate(**annotations)

    @classmethod
    def attach_latest_runs(cls, tasks: list[T]) -> list[T]:
        """
        Populate ``latest_run_*`` attributes on a page of tasks using a single query.

        Resolves the most recent run per task with one ``DISTINCT ON`` query instead of the six
        correlated subqueries ``annotate_latest_run`` would add to the (un-paginated) collection
        query. This keeps the collection scan free of latest-run subqueries unless they are needed
        for filtering or ordering.
        """

        task_ids = [task.pk for task in tasks]
        if task_ids:
            latest_runs = {
                run.task_id: run
                for run in TaskRun.objects
                .filter(task_id__in=task_ids)
                .order_by("task_id", "-started_at", "-id")
                .distinct("task_id")
            }
        else:
            latest_runs = {}

        for task in tasks:
            run = latest_runs.get(task.pk)
            for name, source in cls.latest_run_field_map.items():
                setattr(task, name, getattr(run, source) if run is not None else None)

        return tasks
