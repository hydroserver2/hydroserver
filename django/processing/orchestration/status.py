"""Authoritative display statuses for tasks, runs, and attention badges.

Execution statuses remain unchanged; a successful quality check can report
violations without being a failed execution. Query expressions let collections
filter and sort these same statuses before pagination.
"""

from typing import Literal

from django.db.models import Case, CharField, OuterRef, Q, Subquery, Value, When
from django.utils import timezone


TaskStatus = Literal[
    "OK",
    "Pending",
    "Needs attention",
    "Violations found",
    "Behind schedule",
    "Loading paused",
    "Unknown",
]
ISSUE_STATUSES = ("Needs attention", "Violations found", "Behind schedule")


def run_status_cases(status="status", result="result"):
    """Shared precedence for execution failures, active runs, and violations."""
    violations = (
        Q(**{f"{result}__rules_violated__gt": 0})
        | Q(**{f"{result}__rulesViolated__gt": 0})
        | Q(**{f"{result}__violations__0__isnull": False})
    )
    return [
        When(Q(**{status: "FAILURE"}), then=Value("Needs attention")),
        When(Q(**{f"{status}__in": ["PENDING", "STARTED"]}), then=Value("Pending")),
        When(Q(**{status: "SUCCESS"}) & violations, then=Value("Violations found")),
    ]


def run_status_expression():
    return Case(
        *run_status_cases(),
        When(status="SUCCESS", then=Value("OK")),
        default=Value("Unknown"),
        output_field=CharField(),
    )


def annotate_task_status(queryset, now=None):
    """Add a queryable task status without fetching the run history."""
    from .models import TaskRun

    latest = TaskRun.objects.filter(task_id=OuterRef("pk")).order_by("-started_at", "-id")
    queryset = queryset.alias(
        status_run_status=Subquery(latest.values("status")[:1]),
        status_run_result=Subquery(latest.values("result")[:1]),
    )
    failure, active, violations = run_status_cases("status_run_status", "status_run_result")
    # Errors and violations stay visible when a schedule is paused. Active runs
    # on a paused schedule retain the paused task status.
    return queryset.annotate(
        status=Case(
            failure,
            violations,
            When(periodic_task__enabled=False, then=Value("Loading paused")),
            active,
            When(status_run_status__isnull=True, then=Value("Pending")),
            When(
                status_run_status="SUCCESS",
                periodic_task__enabled=True,
                next_run_at__lt=now or timezone.now(),
                then=Value("Behind schedule"),
            ),
            When(
                Q(status_run_status="SUCCESS")
                & (Q(periodic_task__isnull=True) | Q(next_run_at__isnull=False)),
                then=Value("OK"),
            ),
            default=Value("Unknown"),
            output_field=CharField(),
        )
    )
