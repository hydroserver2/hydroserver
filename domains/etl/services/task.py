import re
import uuid
from urllib.parse import parse_qs, urlparse
from typing import List, Literal, Optional, get_args
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from croniter import croniter
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import IntegrityError
from django.db.models import IntegerField, Q, QuerySet, Subquery, OuterRef
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce
from django.utils import timezone
from django.conf import settings
from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule
from domains.iam.models import APIKey
from domains.etl.models import (
    Task,
    TaskMapping,
    TaskMappingPath,
    TaskRun,
)
from domains.sta.models import ThingFileAttachment, Datastream
from interfaces.api.schemas import (
    TaskFields,
    TaskPostBody,
    TaskPatchBody,
    TaskOrderByFields,
)
from domains.etl.tasks import run_etl_task
from interfaces.api.service import ServiceUtils
from .data_connection import DataConnectionService
from .orchestration_system import OrchestrationSystemService

User = get_user_model()

data_connection_service = DataConnectionService()
orchestration_system_service = OrchestrationSystemService()
AGGREGATION_STATISTICS = (
    "last_value_of_day",
    "simple_mean",
    "time_weighted_daily_mean",
)
AGGREGATION_TIMEZONE_MODES = (
    "daylightSavings",
    "fixedOffset",
)
FIXED_OFFSET_PATTERN = re.compile(r"^[+-]\d{4}$")


class TaskService(ServiceUtils):
    def get_task_for_action(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
        include_mappings: bool = True,
        include_latest_run_result: bool = True,
        raise_400: bool = False,
    ):
        try:
            task = Task.objects
            task = self.annotate_latest_task_result(
                task,
                include_result=include_latest_run_result,
            )
            if not include_mappings:
                task = self.annotate_target_identifiers(task)

            if expand_related:
                task = self.select_expanded_fields(
                    task,
                    include_mappings=include_mappings,
                )
            else:
                task = task.select_related(
                    "periodic_task",
                    "periodic_task__crontab",
                    "periodic_task__interval",
                )
                if include_mappings:
                    task = task.prefetch_related("mappings", "mappings__paths")

            task = task.get(pk=uid)
        except Task.DoesNotExist:
            raise HttpError(404 if not raise_400 else 400, "ETL task does not exist")

        task_permissions = task.get_principal_permissions(
            principal=principal
        )

        if "view" not in task_permissions:
            raise HttpError(404 if not raise_400 else 400, "ETL task does not exist")

        if action not in task_permissions:
            raise HttpError(
                403 if not raise_400 else 400,
                f"You do not have permission to {action} this ETL task",
            )

        return task

    @staticmethod
    def extract_target_identifiers(
        task: Task,
        include_mappings: bool = True,
    ) -> list[str]:
        if include_mappings:
            values = [
                path.target_identifier
                for mapping in task.mappings.all()
                for path in mapping.paths.all()
            ]
        else:
            values = getattr(task, "target_identifiers", None) or []

        target_identifiers: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value is None:
                continue
            normalized = str(value).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            target_identifiers.append(normalized)

        return target_identifiers

    @staticmethod
    def build_task_response(
        task: Task,
        expand: bool = True,
        include_mappings: bool = True,
        include_latest_run_result: bool = True,
        include_data_connection_settings: bool = True,
    ) -> dict:
        response = {
            "id": task.id,
            "name": task.name,
            "task_type": task.task_type,
            "schedule": {
                "start_time": task.periodic_task.start_time,
                "paused": task.paused,
                "next_run_at": task.next_run_at,
                "crontab": " ".join(
                    str(getattr(task.periodic_task.crontab, field))
                    for field in ["minute", "hour", "day_of_month", "month_of_year", "day_of_week"]
                ) if task.periodic_task.crontab else None,
                "interval": task.periodic_task.interval.every if task.periodic_task.interval else None,
                "intervalPeriod": task.periodic_task.interval.period if task.periodic_task.interval else None,
            } if task.periodic_task else None,
            "latest_run": {
                "id": getattr(task, "latest_run_id", None),
                "status": getattr(task, "latest_run_status", None),
                "message": getattr(task, "latest_run_message", None),
                "failure_count": getattr(task, "latest_run_failure_count", None),
                "result": (
                    getattr(task, "latest_run_result", None)
                    if include_latest_run_result
                    else None
                ),
                "started_at": getattr(task, "latest_run_started_at", None),
                "finished_at": getattr(task, "latest_run_finished_at", None),
            } if getattr(task, "latest_run_id", None) else None,
            "extractor_variables": task.extractor_variables,
            "transformer_variables": task.transformer_variables,
            "loader_variables": task.loader_variables,
            "target_identifiers": TaskService.extract_target_identifiers(
                task,
                include_mappings=include_mappings,
            ),
            "mappings": (
                [
                    {
                        "source_identifier": mapping.source_identifier,
                        "paths": [
                            {
                                "target_identifier": path.target_identifier,
                                "data_transformations": path.data_transformations
                            } for path in mapping.paths.all()
                        ]
                    } for mapping in task.mappings.all()
                ]
                if include_mappings
                else []
            )
        }

        if expand:
            response["workspace"] = {
                "id": task.workspace.id,
                "name": task.workspace.name,
                "is_private": task.workspace.is_private,
            }
            response["data_connection"] = (
                {
                    "id": task.data_connection.id,
                    "name": task.data_connection.name,
                    "data_connection_type": task.data_connection.data_connection_type,
                    "workspace_id": task.data_connection.workspace_id,
                    "extractor": {
                        "settings_type": task.data_connection.extractor_type,
                        "settings": task.data_connection.extractor_settings,
                    } if (
                        include_data_connection_settings
                        and task.data_connection.extractor_type
                    ) else None,
                    "transformer": {
                        "settings_type": task.data_connection.transformer_type,
                        "settings": task.data_connection.transformer_settings,
                    } if (
                        include_data_connection_settings
                        and task.data_connection.transformer_type
                    ) else None,
                    "loader": {
                        "settings_type": task.data_connection.loader_type,
                        "settings": task.data_connection.loader_settings,
                    } if (
                        include_data_connection_settings
                        and task.data_connection.loader_type
                    ) else None,
                } if task.data_connection else None
            )
            response["orchestration_system"] = {
                "id": task.orchestration_system.id,
                "name": task.orchestration_system.name,
                "orchestration_system_type": task.orchestration_system.orchestration_system_type,
                "workspace_id": task.orchestration_system.workspace_id
            }
        else:
            response["workspace_id"] = task.workspace_id
            response["data_connection_id"] = task.data_connection_id
            response["orchestration_system_id"] = task.orchestration_system_id

        return response

    @staticmethod
    def select_expanded_fields(
        queryset: QuerySet,
        include_mappings: bool = True,
    ) -> QuerySet:
        queryset = queryset.select_related(
            "data_connection", "workspace", "orchestration_system", "periodic_task", "periodic_task__crontab",
            "periodic_task__interval"
        )
        if include_mappings:
            queryset = queryset.prefetch_related("mappings", "mappings__paths")
        return queryset

    @staticmethod
    def annotate_target_identifiers(queryset: QuerySet) -> QuerySet:
        return queryset.annotate(
            target_identifiers=ArrayAgg(
                "mappings__paths__target_identifier",
                distinct=True,
                filter=(
                    Q(mappings__paths__target_identifier__isnull=False)
                    & ~Q(mappings__paths__target_identifier="")
                ),
            )
        )

    @staticmethod
    def annotate_latest_task_result(
        queryset: QuerySet,
        include_result: bool = True,
    ) -> QuerySet:
        task_result_queryset = (
            TaskRun.objects
            .filter(task_id=OuterRef("pk"))
            .order_by("-started_at")
        )
        annotations = {
            "latest_run_id": Subquery(
                task_result_queryset.values("id")[:1]
            ),
            "latest_run_status": Subquery(
                task_result_queryset.values("status")[:1]
            ),
            "latest_run_message": Subquery(
                task_result_queryset.annotate(
                    message_text=Coalesce(
                        KeyTextTransform("message", "result"),
                        KeyTextTransform("summary", "result"),
                        KeyTextTransform("statusMessage", "result"),
                        KeyTextTransform("status_message", "result"),
                        KeyTextTransform("failureReason", "result"),
                        KeyTextTransform("failure_reason", "result"),
                        KeyTextTransform("error", "result"),
                    )
                ).values("message_text")[:1]
            ),
            "latest_run_failure_count": Subquery(
                task_result_queryset.annotate(
                    failure_count_value=Coalesce(
                        Cast(
                            KeyTextTransform("failure_count", "result"),
                            IntegerField(),
                        ),
                        Cast(
                            KeyTextTransform("failureCount", "result"),
                            IntegerField(),
                        ),
                        output_field=IntegerField(),
                    )
                ).values("failure_count_value")[:1]
            ),
            "latest_run_started_at": Subquery(
                task_result_queryset.values("started_at")[:1]
            ),
            "latest_run_finished_at": Subquery(
                task_result_queryset.values("finished_at")[:1]
            ),
        }
        if include_result:
            annotations["latest_run_result"] = Subquery(
                task_result_queryset.values("result")[:1]
            )
        return queryset.annotate(
            **annotations
        )

    def list(
        self,
        principal: Optional[User | APIKey],
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        expand_related: Optional[bool] = None,
        include_mappings: Optional[bool] = None,
        include_latest_run_result: Optional[bool] = None,
        include_data_connection_settings: Optional[bool] = None,
    ):
        include_mappings = True if include_mappings is None else include_mappings
        include_latest_run_result = (
            True
            if include_latest_run_result is None
            else include_latest_run_result
        )
        include_data_connection_settings = (
            True
            if include_data_connection_settings is None
            else include_data_connection_settings
        )
        queryset = Task.objects

        queryset = self.annotate_latest_task_result(
            queryset,
            include_result=include_latest_run_result,
        )

        for field in [
            "workspace_id",
            "task_type",
            "data_connection_id",
            "orchestration_system_id",
            "orchestration_system__type",
            "latest_run_status",
            "latest_run_started_at__lte",
            "latest_run_started_at__gte",
            "latest_run_finished_at__lte",
            "latest_run_finished_at__gte",
            "next_run_at__lte",
            "next_run_at__gte",
            "paused",
            "periodic_task__start_time__lte",
            "periodic_task__start_time__gte",
            "data_connection__data_connection_type",
            "data_connection__extractor_type",
            "data_connection__transformer_type",
            "data_connection__loader_type",
            "mappings__source_identifier",
            "mappings__paths__target_identifier",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if not include_mappings:
            queryset = self.annotate_target_identifiers(queryset)

        if order_by:
            order_by_aliases = {
                "type": "task_type",
                "orchestrationSystemType": "orchestration_system__type",
                "startTime": "periodic_task__start_time",
                "dataConnectionType": "data_connection__data_connection_type",
                "dataConnectionExtractorType": "data_connection__extractor_type",
                "dataConnectionTransformerType": "data_connection__transformer_type",
                "dataConnectionLoaderType": "data_connection__loader_type",
            }
            order_by_aliases.update(
                {f"-{key}": f"-{value}" for key, value in order_by_aliases.items()}
            )

            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(TaskOrderByFields)),
                field_aliases=order_by_aliases,
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(
                queryset,
                include_mappings=include_mappings,
            )
        else:
            queryset = queryset.select_related(
                "periodic_task",
                "periodic_task__crontab",
                "periodic_task__interval",
            )
            if include_mappings:
                queryset = queryset.prefetch_related("mappings", "mappings__paths")

        queryset = queryset.visible(principal=principal).distinct()  # noqa
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            self.build_task_response(
                task,
                expand=expand_related,
                include_mappings=include_mappings,
                include_latest_run_result=include_latest_run_result,
                include_data_connection_settings=include_data_connection_settings,
            ) for task in queryset.all()
        ]

    def get(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        task = self.get_task_for_action(
            principal=principal,
            uid=uid,
            action="view",
            expand_related=expand_related,
        )

        return self.build_task_response(task, expand=expand_related)

    def create(
        self,
        principal: User | APIKey,
        data: TaskPostBody,
    ):
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=data.workspace_id
        )

        if not Task.can_principal_create(
            principal=principal, workspace=workspace
        ):
            raise HttpError(
                403, "You do not have permission to create this task"
            )

        task_type = data.task_type or "ETL"

        data_connection = None
        if task_type == "Aggregation":
            if data.data_connection_id is not None:
                raise HttpError(400, "Aggregation tasks cannot define a data connection.")
        else:
            if data.data_connection_id is None:
                raise HttpError(400, "ETL tasks require a data connection.")
            data_connection = data_connection_service.get_data_connection_for_action(
                principal=principal, uid=data.data_connection_id, action="edit", raise_400=True, expand_related=True
            )

            if data_connection.workspace and data_connection.workspace_id != workspace.id:
                raise HttpError(400, "Task and data connection must belong to the same workspace.")

        orchestration_system = orchestration_system_service.get_orchestration_system_for_action(
            principal=principal, uid=data.orchestration_system_id, action="view", raise_400=True
        )

        if orchestration_system.workspace and orchestration_system.workspace_id != workspace.id:
            raise HttpError(400, "Task and orchestration system must belong to the same workspace.")

        try:
            task = Task.objects.create(
                pk=data.id,
                name=data.name,
                task_type=task_type,
                workspace=workspace,
                data_connection=data_connection,
                orchestration_system=orchestration_system,
                extractor_variables=data.extractor_variables or {},
                transformer_variables=data.transformer_variables or {},
                loader_variables=data.loader_variables or {},
            )
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        task = self.update_scheduling(task, data.schedule.dict() if data.schedule else None)
        task = self.update_mapping(
            task,
            [mapping.dict() for mapping in data.mappings]
            if data.mappings is not None
            else None,
        )
        task.save()

        return self.get(
            principal=principal, uid=task.id, expand_related=True
        )

    def update(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        data: TaskPatchBody,
    ):
        task = self.get_task_for_action(
            principal=principal, uid=uid, action="edit"
        )
        task_data = data.dict(
            include=set(TaskFields.model_fields.keys()) | {"schedule", "mappings", "data_connection_id", "orchestration_system_id"},
            exclude_unset=True,
        )

        next_task_type = task_data.get("task_type", task.task_type)

        if next_task_type == "Aggregation":
            if "data_connection_id" in task_data and task_data["data_connection_id"] is not None:
                raise HttpError(400, "Aggregation tasks cannot define a data connection.")
            task_data["data_connection_id"] = None
        else:
            next_data_connection_id = task_data.get("data_connection_id", task.data_connection_id)
            if not next_data_connection_id:
                raise HttpError(400, "ETL tasks require a data connection.")

            if "data_connection_id" in task_data and task_data["data_connection_id"] is not None:
                data_connection = data_connection_service.get_data_connection_for_action(
                    principal=principal, uid=data.data_connection_id, action="edit", raise_400=True, expand_related=True
                )

                if data_connection.workspace_id != task.workspace_id:
                    raise HttpError(400, "Task and data connection must belong to the same workspace.")

        if "orchestration_system_id" in task_data:
            orchestration_system = orchestration_system_service.get_orchestration_system_for_action(
                principal=principal, uid=data.orchestration_system_id, action="view", raise_400=True
            )

            if orchestration_system.workspace and orchestration_system.workspace_id != task.workspace_id:
                raise HttpError(400, "Task and orchestration system must belong to the same workspace.")

        task.task_type = next_task_type

        if "schedule" in task_data:
            task = self.update_scheduling(task, task_data["schedule"])

        if "mappings" in task_data:
            task = self.update_mapping(task, task_data["mappings"])

        for field, value in task_data.items():
            if field not in {"schedule", "mappings"}:
                setattr(task, field, value)
            if field == "schedule":
                if "paused" in value:
                    task.paused = value["paused"]
                if "next_run_at" in value:
                    task.next_run_at = value["next_run_at"]

        task.save()

        return self.get(
            principal=principal, uid=task.id, expand_related=True
        )

    def delete(self, principal: User | APIKey, uid: uuid.UUID):
        task = self.get_task_for_action(
            principal=principal, uid=uid, action="delete", expand_related=True
        )

        task.delete()

        return "ETL Task deleted"

    def run(self, principal: User | APIKey, task_id: uuid.UUID, file=None):
        """"""

        task = self.get_task_for_action(
            principal=principal, uid=task_id, action="edit", expand_related=True
        )

        if task.orchestration_system.orchestration_system_type != "INTERNAL":
            raise HttpError(400, "Cannot run task managed by external orchestration system")

        run_id = uuid.uuid4()
        task_run = TaskRun.objects.create(
            id=run_id,
            task=task,
            status="RUNNING",
            started_at=timezone.now(),
        )

        try:
            if settings.CELERY_ENABLED is True:
                run_etl_task.apply_async(
                    kwargs={"task_id": str(task.id)},
                    task_id=str(run_id),
                )
            else:
                run_etl_task.apply(
                    kwargs={"task_id": str(task.id)},
                    task_id=str(run_id),
                )
        except Exception:
            task_run.delete()
            raise

        task_run.refresh_from_db()

        return {
            "id": task_run.id,
            "status": task_run.status,
            "message": task_run.message,
            "failure_count": task_run.failure_count,
            "result": task_run.result,
            "started_at": task_run.started_at,
            "finished_at": task_run.finished_at,
        }

    @staticmethod
    def update_scheduling(task: Task, schedule_data: dict | None = None):
        if task.periodic_task and schedule_data is None:
            if task.periodic_task.crontab:
                task.periodic_task.crontab.delete()
            if task.periodic_task.interval:
                task.periodic_task.interval.delete()
            task.periodic_task.delete()

            task.periodic_task = None
            task.next_run_at = None
            task.paused = False

            return task

        if not schedule_data:
            return task

        crontab_schedule = task.periodic_task.crontab if task.periodic_task else None
        interval_schedule = task.periodic_task.interval if task.periodic_task else None

        if "interval" in schedule_data or "interval_period" in schedule_data:
            if "interval" not in schedule_data:
                every = (
                    task.periodic_task.interval.every if task.periodic_task and task.periodic_task.interval else None
                )
            else:
                every = schedule_data["interval"]

            if "interval_period" in schedule_data:
                period = schedule_data["interval_period"]
            else:
                period = (
                    task.periodic_task.interval.period if task.periodic_task and task.periodic_task.interval else None
                )

            if (every is None) != (period is None):
                raise HttpError(400, "Both schedule interval and period must be defined")

            schedule_data["interval"] = f"{every} {period}" if every and period else None

        if "crontab" in schedule_data:
            if task.periodic_task and task.periodic_task.crontab and schedule_data["crontab"] is None:
                task.periodic_task.crontab.delete()
                task.periodic_task.crontab = None
                crontab_schedule = None

            elif schedule_data["crontab"] is not None:
                try:
                    croniter(schedule_data["crontab"], datetime.now())
                    minute, hour, day, month, weekday = schedule_data["crontab"].strip().split()
                except (ValueError, AttributeError):
                    raise HttpError(400, "Invalid crontab schedule")

                if task.periodic_task and task.periodic_task.crontab:
                    task.periodic_task.crontab.minute = minute
                    task.periodic_task.crontab.hour = hour
                    task.periodic_task.crontab.day_of_month = day
                    task.periodic_task.crontab.month_of_year = month
                    task.periodic_task.crontab.day_of_week = weekday
                    task.periodic_task.crontab.save()
                else:
                    crontab_schedule = CrontabSchedule.objects.create(
                        minute=minute,
                        hour=hour,
                        day_of_month=day,
                        month_of_year=month,
                        day_of_week=weekday,
                    )

        if "interval" in schedule_data:
            if task.periodic_task and task.periodic_task.interval and schedule_data["interval"] is None:
                task.periodic_task.interval.delete()
                task.periodic_task.interval = None
                interval_schedule = None

            elif schedule_data["interval"] is not None:
                try:
                    every_str, period = schedule_data["interval"].strip().split()
                    every = int(every_str)
                    if period not in {"minutes", "hours", "days"}:
                        raise ValueError
                except ValueError:
                    raise HttpError(400, "Invalid interval schedule")

                if task.periodic_task and task.periodic_task.interval:
                    task.periodic_task.interval.every = every
                    task.periodic_task.interval.period = period
                    task.periodic_task.interval.save()
                else:
                    interval_schedule = IntervalSchedule.objects.create(
                        every=every, period=period
                    )

        if not interval_schedule and not crontab_schedule:
            raise HttpError(400, "No schedule defined")

        if not task.periodic_task:
            task.periodic_task = PeriodicTask.objects.create(
                name=f"{task.name} — {task.id}",
                task="domains.etl.tasks.run_etl_task",
                kwargs=f'{{"task_id": "{str(task.id)}"}}',
                enabled=True,
                date_changed=timezone.now(),
                interval=interval_schedule,
                crontab=crontab_schedule,
                start_time=schedule_data.get("start_time", timezone.now()),
                expire_seconds=3600,
            )
        else:
            task.periodic_task.crontab = crontab_schedule
            task.periodic_task.interval = interval_schedule

        if not task.periodic_task:
            return task

        if "start_time" in schedule_data:
            task.periodic_task.start_time = schedule_data["start_time"]

        task.periodic_task.enabled = (
            task.orchestration_system.orchestration_system_type == "INTERNAL"
            and not schedule_data.get("paused", False)
        )
        task.periodic_task.date_changed = timezone.now()

        if task.periodic_task.interval and task.periodic_task.crontab:
            raise HttpError(400, "Only one of interval or crontab can be set")

        task.periodic_task.save()

        return task

    @staticmethod
    def _extract_rating_curve_url(transformation: dict) -> str:
        url = transformation.get("ratingCurveUrl")
        if isinstance(url, str) and url.strip():
            return url.strip()

        raise HttpError(400, "Rating curve transformations must define ratingCurveUrl")

    @staticmethod
    def _normalize_transformation(transformation: dict) -> dict:
        normalized = dict(transformation or {})
        transform_type = normalized.get("type")

        if transform_type == "rating_curve":
            rating_curve_url = TaskService._extract_rating_curve_url(normalized)
            normalized["ratingCurveUrl"] = rating_curve_url

        return normalized

    @staticmethod
    def _validate_aggregation_mapping_constraints(
        workspace_id: uuid.UUID,
        mapping_data: List[dict],
    ):
        if len(mapping_data) < 1:
            raise HttpError(
                400,
                "Aggregation tasks must include at least one mapping.",
            )

        datastream_ids: set[uuid.UUID] = set()
        for mapping in mapping_data:
            try:
                source_identifier = str(uuid.UUID(str(mapping["source_identifier"])))
            except (KeyError, ValueError, TypeError):
                raise HttpError(400, "Aggregation mappings require a valid source datastream UUID.")

            paths = mapping.get("paths", []) or []
            if len(paths) != 1:
                raise HttpError(
                    400,
                    "Aggregation mappings currently support exactly one target path per source.",
                )

            mapping["source_identifier"] = source_identifier
            datastream_ids.add(uuid.UUID(source_identifier))

            path = paths[0]
            try:
                target_identifier = str(uuid.UUID(str(path["target_identifier"])))
            except (KeyError, ValueError, TypeError):
                raise HttpError(400, "Aggregation mappings require a valid target datastream UUID.")

            path["target_identifier"] = target_identifier
            datastream_ids.add(uuid.UUID(target_identifier))

            transformations = path.get("data_transformations", []) or []
            if not isinstance(transformations, list) or len(transformations) != 1:
                raise HttpError(
                    400,
                    "Aggregation mappings require exactly one aggregation transformation per path.",
                )

            if not isinstance(transformations[0], dict):
                raise HttpError(400, "Invalid aggregation data transformation payload.")

            path["data_transformations"] = [
                TaskService._validate_aggregation_transformation(transformations[0])
            ]

        existing_datastream_ids = set(
            Datastream.objects.filter(
                thing__workspace_id=workspace_id,
                id__in=datastream_ids,
            ).values_list("id", flat=True)
        )
        missing = sorted(str(uid) for uid in (datastream_ids - existing_datastream_ids))
        if missing:
            raise HttpError(
                400,
                "Aggregation mapping datastreams must exist in the task workspace.",
            )

    @staticmethod
    def _validate_aggregation_transformation(transformation: dict) -> dict:
        normalized = dict(transformation or {})

        if normalized.get("type") != "aggregation":
            raise HttpError(400, "Aggregation transformation must set type='aggregation'")

        aggregation_statistic = normalized.get("aggregationStatistic")
        if aggregation_statistic not in AGGREGATION_STATISTICS:
            allowed = ", ".join(AGGREGATION_STATISTICS)
            raise HttpError(400, f"aggregationStatistic must be one of: {allowed}")

        timezone_mode = normalized.get("timezoneMode")
        if timezone_mode not in AGGREGATION_TIMEZONE_MODES:
            allowed = ", ".join(AGGREGATION_TIMEZONE_MODES)
            raise HttpError(400, f"timezoneMode must be one of: {allowed}")

        timezone_value = normalized.get("timezone")
        if not isinstance(timezone_value, str) or not timezone_value.strip():
            raise HttpError(400, "timezone is required for aggregation transformations")

        timezone_value = timezone_value.strip()
        if timezone_mode == "fixedOffset":
            if not FIXED_OFFSET_PATTERN.fullmatch(timezone_value):
                raise HttpError(400, "fixedOffset timezone must match +/-HHMM")
            if int(timezone_value[-2:]) > 59:
                raise HttpError(400, "fixedOffset timezone minutes must be between 00 and 59")
        else:
            try:
                ZoneInfo(timezone_value)
            except ZoneInfoNotFoundError as exc:
                raise HttpError(400, "daylightSavings timezone must be a valid IANA timezone") from exc

        normalized["timezone"] = timezone_value

        return normalized

    @staticmethod
    def _reject_aggregation_transformations(mapping_data: List[dict]):
        for mapping in mapping_data:
            for path in mapping.get("paths", []) or []:
                transformations = path.get("data_transformations", []) or []
                if not isinstance(transformations, list):
                    raise HttpError(
                        400,
                        "Path data_transformations must be an array of transformation objects",
                    )

                for transformation in transformations:
                    if not isinstance(transformation, dict):
                        raise HttpError(400, "Invalid data transformation payload")
                    if transformation.get("type") == "aggregation":
                        raise HttpError(
                            400,
                            "Aggregation transformations are only valid when task type is Aggregation.",
                        )

    @staticmethod
    def _thing_attachment_rating_curve_references(
        workspace_id: uuid.UUID,
    ) -> set[tuple[uuid.UUID, int, uuid.UUID]]:
        return set(
            ThingFileAttachment.objects.filter(
                thing__workspace_id=workspace_id,
                file_attachment_type="rating_curve",
            ).values_list("thing_id", "id", "download_token")
        )

    @staticmethod
    def _parse_thing_attachment_reference(
        rating_curve_url: str,
    ) -> tuple[uuid.UUID, int, uuid.UUID] | None:
        parsed = urlparse(rating_curve_url)
        path_segments = [segment for segment in parsed.path.split("/") if segment]
        if len(path_segments) < 5:
            return None

        if path_segments[-1] != "download":
            return None
        if path_segments[-3] != "file-attachments":
            return None
        if path_segments[-5] != "things":
            return None

        try:
            thing_id = uuid.UUID(path_segments[-4])
        except ValueError:
            return None

        try:
            attachment_id = int(path_segments[-2])
        except ValueError:
            return None

        query = parse_qs(parsed.query)
        token = (query.get("token") or [None])[0]
        if not token:
            return None

        try:
            download_token = uuid.UUID(token)
        except ValueError:
            return None

        return thing_id, attachment_id, download_token

    @staticmethod
    def _validate_rating_curve_transformation_references(
        workspace_id: uuid.UUID, mapping_data: List[dict]
    ):
        valid_references = TaskService._thing_attachment_rating_curve_references(
            workspace_id
        )

        for mapping in mapping_data:
            for path in mapping.get("paths", []):
                transformations = path.get("data_transformations", []) or []
                if not isinstance(transformations, list):
                    raise HttpError(
                        400,
                        "Path data_transformations must be an array of transformation objects",
                    )

                normalized_transformations = []
                for transformation in transformations:
                    if not isinstance(transformation, dict):
                        raise HttpError(400, "Invalid data transformation payload")

                    normalized = TaskService._normalize_transformation(transformation)

                    if normalized.get("type") == "rating_curve":
                        rating_curve_url = TaskService._extract_rating_curve_url(normalized)
                        reference = TaskService._parse_thing_attachment_reference(
                            rating_curve_url
                        )
                        if not reference or reference not in valid_references:
                            raise HttpError(
                                400,
                                "ratingCurveUrl must reference an existing thing rating curve attachment in the task workspace",
                            )

                    normalized_transformations.append(normalized)

                path["data_transformations"] = normalized_transformations

    @staticmethod
    def update_mapping(task: Task, mapping_data: List[dict] | None = None):
        if mapping_data is None:
            return task

        if task.task_type == "Aggregation":
            TaskService._validate_aggregation_mapping_constraints(
                workspace_id=task.workspace_id, mapping_data=mapping_data
            )
        else:
            TaskService._reject_aggregation_transformations(mapping_data)
            TaskService._validate_rating_curve_transformation_references(
                workspace_id=task.workspace_id, mapping_data=mapping_data
            )

        task.mappings.all().delete()

        for mapping in mapping_data:
            task_mapping = TaskMapping.objects.create(
                task=task, source_identifier=mapping["source_identifier"]
            )
            for path in mapping["paths"]:
                TaskMappingPath.objects.create(
                    task_mapping=task_mapping,
                    target_identifier=path["target_identifier"],
                    data_transformations=path.get("data_transformations", []),
                )

        return task
