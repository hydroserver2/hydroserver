import uuid
import uuid6
import logging
import numpy as np
import pandas as pd

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Union, Literal

from pydantic import Field, ConfigDict, validate_call
from ninja.errors import HttpError
from django.db import transaction
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector, SearchQuery
from django.utils import timezone

from core.types import Unset
from core.iam.models import APIKey, Workspace
from core.service import ServiceUtils
from core.sta.models import Thing
from core.sta.models.observation import Observation
from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL
from processing.orchestration.services import TaskService
from processing.monitoring.exceptions import MonitoringError
from processing.monitoring.models import MonitoringTask, MonitoringNotificationRecipient, MonitoringRule
from processing.monitoring.services.rule import MonitoringRuleService


User = get_user_model()

CELERY_TASK_NAME = "processing.monitoring.tasks.run_monitoring_task"

logger = logging.getLogger(__name__)

rule_service = MonitoringRuleService()


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

    @staticmethod
    def _fetch_observations(datastream, after=None) -> pd.DataFrame:
        """Fetch observations for a datastream as a canonical pandas timeseries DataFrame."""

        qs = Observation.objects.filter(datastream=datastream).order_by("phenomenon_time")
        if after is not None:
            qs = qs.filter(phenomenon_time__gte=after)

        data = list(qs.values_list("phenomenon_time", "result"))
        if not data:
            return pd.DataFrame({
                TIMESTAMP_COL: pd.Series([], dtype="datetime64[us, UTC]"),
                RESULT_COL: pd.Series([], dtype=np.float64),
            })

        timestamps, results = zip(*data)
        return pd.DataFrame({
            TIMESTAMP_COL: pd.DatetimeIndex(timestamps).as_unit("us"),
            RESULT_COL: np.array(results, dtype=np.float64),
        })

    @staticmethod
    def _rule_fetch_start(rule: MonitoringRule, datastream) -> datetime | None:
        """Compute the earliest timestamp needed to check this rule, or None for missing_data rules."""

        if rule.rule_type == "missing_data":
            return None

        if rule.window_interval and rule.window_interval_units:
            window_td = timedelta(**{rule.window_interval_units: rule.window_interval})
        else:
            window_td = None

        if rule.last_checked_at is not None:
            return rule.last_checked_at - window_td if window_td else rule.last_checked_at
        else:
            return datastream.phenomenon_begin_time

    @staticmethod
    def _slice_df_for_rule(df: pd.DataFrame, rule: MonitoringRule) -> pd.DataFrame:
        """Slice the full datastream DataFrame to the range required by this rule."""

        if rule.window_interval and rule.window_interval_units:
            window_td = timedelta(**{rule.window_interval_units: rule.window_interval})
        else:
            window_td = None

        if rule.last_checked_at is not None:
            if window_td:
                start = rule.last_checked_at - window_td
                return df[df[TIMESTAMP_COL] >= start].reset_index(drop=True)
            else:
                return df[df[TIMESTAMP_COL] > rule.last_checked_at].reset_index(drop=True)

        return df

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def run(
        self,
        task: Union[uuid.UUID, MonitoringTask],
        principal: User | APIKey | None | Unset = Unset,
    ) -> dict:
        """
        Run all monitoring rules for this task.

        Fetches each datastream's observations once, runs all associated rules against it,
        then moves on to the next datastream. Updates last_checked_at on each rule that
        runs without error. Raises MonitoringError if any checks fail, so the TaskRun
        is marked FAILURE while still recording the full summary.
        """

        task = self.get(task=task, principal=principal)

        rules = list(
            task.rules.select_related("datastream").order_by("datastream_id")
        )

        if not rules:
            return {"message": "No rules configured for this task."}

        rules_by_datastream = defaultdict(list)
        for rule in rules:
            rules_by_datastream[rule.datastream_id].append(rule)

        total_checked = 0
        total_violated = 0
        total_errored = 0
        violations = []
        errors = []

        for datastream_id, datastream_rules in rules_by_datastream.items():
            datastream = datastream_rules[0].datastream

            if not datastream.phenomenon_begin_time:
                logger.debug("Skipping datastream %s: no data.", datastream_id)
                continue

            fetch_starts = [
                self._rule_fetch_start(rule, datastream)
                for rule in datastream_rules
            ]
            fetch_start = min((s for s in fetch_starts if s is not None), default=None)

            fetched_at = timezone.now()
            df = self._fetch_observations(datastream, after=fetch_start)

            logger.debug(
                "Fetched %d observation(s) for datastream %s.",
                len(df), datastream_id,
            )

            successful_rule_ids = []

            for rule in datastream_rules:
                total_checked += 1
                try:
                    rule_df = self._slice_df_for_rule(df, rule)
                    result = rule_service.check_rule(rule, rule_df, datastream)

                    if result["violated"]:
                        total_violated += 1
                        violations.append({
                            "rule_id": str(rule.id),
                            "datastream_id": str(datastream_id),
                            "rule_type": rule.rule_type,
                            "violation_count": result["violation_count"],
                            "first_violation_at": (
                                result["first_violation_at"].isoformat()
                                if result["first_violation_at"] else None
                            ),
                            "last_violation_at": (
                                result["last_violation_at"].isoformat()
                                if result["last_violation_at"] else None
                            ),
                        })

                    successful_rule_ids.append(rule.id)

                except Exception as e:
                    total_errored += 1
                    errors.append({
                        "rule_id": str(rule.id),
                        "datastream_id": str(datastream_id),
                        "rule_type": rule.rule_type,
                        "error": str(e),
                    })
                    logger.error(
                        "Rule check failed for rule %s (%s) on datastream %s.",
                        rule.id, rule.rule_type, datastream_id,
                        exc_info=True,
                    )

            if successful_rule_ids:
                MonitoringRule.objects.filter(pk__in=successful_rule_ids).update(
                    last_checked_at=fetched_at
                )

        summary = {
            "rules_checked": total_checked,
            "rules_violated": total_violated,
            "rules_errored": total_errored,
            "violations": violations,
            "errors": errors,
        }

        if total_violated or total_errored:
            recipient_emails = list(task.recipients.values_list("email", flat=True))
            if recipient_emails:
                try:
                    self._send_violation_notification(task, summary, rules)
                except Exception as e:
                    e.result = summary
                    raise

        if total_errored:
            exc = MonitoringError(
                f"{total_errored} of {total_checked} rule check(s) encountered an error."
            )
            exc.result = summary
            raise exc

        if total_violated:
            message = f"{total_violated} of {total_checked} rule(s) have violations."
        else:
            message = f"All {total_checked} rule(s) passed."

        return {"message": message, **summary}

    @staticmethod
    def _send_violation_notification(
        task: MonitoringTask,
        summary: dict,
        rules: list,
    ) -> None:
        from django.core.mail import send_mail
        from django.conf import settings

        recipient_emails = list(task.recipients.values_list("email", flat=True))
        if not recipient_emails:
            return

        rule_lookup = {str(rule.id): rule for rule in rules}

        def _fmt(iso_str: str | None) -> str:
            return iso_str if iso_str else "unknown"

        def _violation_detail(v: dict, rule) -> list[str]:
            rt = v["rule_type"]
            count = v["violation_count"]
            first = _fmt(v["first_violation_at"])
            last = _fmt(v["last_violation_at"])

            if rt == "missing_data":
                interval = f"{rule.window_interval} {rule.window_interval_units}" if rule else "configured interval"
                return [
                    f"  [missing_data]",
                    f"    No new data since {first}. Expected data every {interval}.",
                ]

            if rt == "range" and rule:
                if rule.min_value is not None and rule.max_value is not None:
                    bound_str = f"outside allowed range [{rule.min_value}, {rule.max_value}]"
                elif rule.min_value is not None:
                    bound_str = f"below minimum of {rule.min_value}"
                else:
                    bound_str = f"above maximum of {rule.max_value}"
                detail = f"{count} value(s) {bound_str}."
            elif rt == "rate_of_change" and rule:
                detail = (
                    f"{count} value(s) exceeded the maximum rate of change of {rule.max_value}"
                    f" per {rule.window_interval} {rule.window_interval_units}."
                )
            elif rt == "persistence" and rule:
                detail = f"{count} value(s) showed no change over {rule.window_interval} {rule.window_interval_units}."
            else:
                detail = f"{count} value(s) in violation."

            return [
                f"  [{rt}]",
                f"    {detail}",
                f"    First violation: {first}",
                f"    Last violation:  {last}",
            ]

        lines = [
            f'Monitoring task "{task.name}" on thing "{task.thing.name}" detected issues during its latest run.',
            "",
            "Summary",
            "-------",
            f"Rules checked:         {summary['rules_checked']}",
            f"Rules with violations: {summary['rules_violated']}",
            f"Rules with errors:     {summary['rules_errored']}",
        ]

        if summary["violations"]:
            lines += ["", "", "VIOLATIONS", "=========="]

            violations_by_ds: dict[str, list] = defaultdict(list)
            for v in summary["violations"]:
                violations_by_ds[v["datastream_id"]].append(v)

            for ds_id, ds_violations in violations_by_ds.items():
                ds_name = next(
                    (r.datastream.name for r in rules if str(r.datastream_id) == ds_id),
                    ds_id,
                )
                lines.append(f"\nDatastream: {ds_name}")
                for v in ds_violations:
                    rule = rule_lookup.get(v["rule_id"])
                    lines.extend(_violation_detail(v, rule))

        if summary["errors"]:
            lines += ["", "", "ERRORS", "======"]
            for e in summary["errors"]:
                rule = rule_lookup.get(e["rule_id"])
                ds_name = rule.datastream.name if rule else e["datastream_id"]
                lines += [
                    f"\n  [{e['rule_type']}] on datastream {ds_name}",
                    f"    {e['error']}",
                ]

        send_mail(
            subject=f"[HydroServer] Monitoring Alert: {task.name}",
            message="\n".join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_emails,
            fail_silently=False,
        )
