"""Shared definition of which orchestration tasks "need attention".

This mirrors the frontend status logic in
``apps/data-management/src/utils/orchestration/taskRunDetails.ts`` so that the
per-connection / per-thing attention badges agree with the per-task statuses
shown in the task list.

A task needs attention when either:

* its latest run FAILED ("Needs attention"), or
* it is "Behind schedule": an *enabled* schedule whose latest run completed
  *successfully* but whose ``next_run_at`` is already in the past.

Tasks that are paused (schedule disabled), currently running/queued
(``PENDING``/``STARTED``), or have never run are intentionally excluded from the
behind-schedule case. The frontend shows those as "Loading paused" / "Pending",
which are not treated as issues, so counting them here would inflate the badge
relative to the task list.
"""

from django.db.models import OuterRef, Q, Subquery


def latest_run_status_subquery():
    """Correlated subquery selecting the status of a task's most recent run.

    ``OuterRef("pk")`` resolves to the task being annotated, so this can be
    dropped into any ``Task`` (EtlTask / DataProductTask / MonitoringTask)
    queryset via ``.annotate(latest_run_status=latest_run_status_subquery())``.
    """
    from .models import TaskRun

    return Subquery(
        TaskRun.objects
        .filter(task_id=OuterRef("pk"))
        .order_by("-started_at", "-id")
        .values("status")[:1]
    )


def attention_filter(now):
    """Q expression for tasks needing attention.

    Requires the queryset to be annotated with ``latest_run_status`` (see
    :func:`latest_run_status_subquery`). ``now`` is the reference time used to
    decide whether a task is overdue.
    """
    behind_schedule = (
        Q(latest_run_status="SUCCESS")
        & Q(periodic_task__enabled=True)
        & Q(next_run_at__lt=now)
    )
    return Q(latest_run_status="FAILURE") | behind_schedule
