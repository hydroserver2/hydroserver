import logging
import numpy as np
import pandas as pd

from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID

from celery import shared_task
from django.utils import timezone

from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL
from hydroserverpy.quality.check import check_range, check_rate_of_change, check_persistence

from core.sta.models.observation import Observation
from processing.monitoring.exceptions import MonitoringError
from processing.monitoring.models import MonitoringTask, MonitoringRule


logger = logging.getLogger(__name__)

_UNIT_TO_DURATION = {"minutes": "m", "hours": "h", "days": "d"}


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


def check_rule(rule: MonitoringRule, df, datastream) -> dict:
    """
    Run a single rule check against a pre-sliced DataFrame.

    Returns a dict with violated, violation_count, first_violation_at, last_violation_at.
    For missing_data rules the df is unused; the datastream's phenomenon_end_time is checked
    directly against the rule's window.
    """

    no_data_value = datastream.no_data_value

    if rule.rule_type == "missing_data":
        window_td = timedelta(**{rule.window_interval_units: rule.window_interval})
        end_time = datastream.phenomenon_end_time
        violated = end_time is None or (timezone.now() - end_time) > window_td
        return {
            "violated": violated,
            "violation_count": 1 if violated else 0,
            "first_violation_at": end_time if violated else None,
            "last_violation_at": None,
        }

    if rule.rule_type == "range":
        result = check_range(
            df,
            min_value=rule.min_value,
            max_value=rule.max_value,
            no_data_value=no_data_value,
        )
        timestamps = result["timestamps"]

    elif rule.rule_type == "rate_of_change":
        window = f"{rule.window_interval}{_UNIT_TO_DURATION[rule.window_interval_units]}"
        result = check_rate_of_change(
            df,
            window=window,
            max_change=rule.max_value,
            no_data_value=no_data_value,
        )
        timestamps = result["timestamps"]

    elif rule.rule_type == "persistence":
        window = f"{rule.window_interval}{_UNIT_TO_DURATION[rule.window_interval_units]}"
        result = check_persistence(
            df,
            window=window,
            min_value=rule.min_value,
            max_value=rule.max_value,
            no_data_value=no_data_value,
        )
        timestamps = result["timestamps"]

    else:
        raise ValueError(f"Unhandled rule_type '{rule.rule_type}'.")

    if result["violation_count"] > 0:
        return {
            "violated": True,
            "violation_count": result["violation_count"],
            "first_violation_at": timestamps[0],
            "last_violation_at": timestamps[-1],
        }

    return {
        "violated": False,
        "violation_count": 0,
        "first_violation_at": None,
        "last_violation_at": None,
    }


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
        f'Monitoring task "{task.name}" on monitoring_site "{task.monitoring_site.name}" detected issues during its latest run.',
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


@shared_task(bind=True, name="processing.monitoring.tasks.run_monitoring_task")
def run_monitoring_task(self, task_id: str, run_id: str | None = None):
    """
    Runs a HydroServer monitoring task based on the task configuration provided.

    Fetches each datastream's observations once, runs all associated rules against it,
    then moves on to the next datastream. Updates last_checked_at on each rule that
    runs without error. Raises MonitoringError if any checks fail, so the TaskRun
    is marked FAILURE while still recording the full summary.
    """

    try:
        try:
            task = MonitoringTask.objects.select_related("monitoring_site").get(pk=UUID(task_id))
        except MonitoringTask.DoesNotExist:
            raise LookupError(f"Monitoring task with ID {task_id} does not exist.")

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

            fetch_starts = [
                _rule_fetch_start(rule, datastream)
                for rule in datastream_rules
            ]
            fetch_start = min((s for s in fetch_starts if s is not None), default=None)

            fetched_at = timezone.now()
            df = _fetch_observations(datastream, after=fetch_start)

            logger.debug(
                "Fetched %d observation(s) for datastream %s.",
                len(df), datastream_id,
            )

            successful_rule_ids = []

            for rule in datastream_rules:
                total_checked += 1
                try:
                    rule_df = _slice_df_for_rule(df, rule)
                    result = check_rule(rule, rule_df, datastream)

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
                    _send_violation_notification(task, summary, rules)
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
    except MonitoringError as e:
        raise e
    except Exception as e:
        raise Exception("Encountered an unexpected data monitoring error.") from e
