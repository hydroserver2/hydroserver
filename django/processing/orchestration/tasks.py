import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from processing.orchestration.models import Task, TaskRun

STALE_PENDING_MINUTES = 60


@shared_task(bind=True, expires=10)
def cleanup_task_runs(self, days=14, stale_pending_minutes=STALE_PENDING_MINUTES):
    """
    Delete TaskRun records older than `days` days, keeping the most recent
    run per task regardless of age. Also deletes PENDING runs that have not
    transitioned to STARTED within `stale_pending_minutes` minutes.
    """

    now = timezone.now()
    cutoff = now - timedelta(days=days)
    pending_cutoff = now - timedelta(minutes=stale_pending_minutes)
    total_deleted = 0

    tasks = Task.objects.filter(runs__started_at__lt=cutoff).distinct()

    for task in tasks:
        most_recent_pk = (
            TaskRun.objects.filter(task=task)
            .order_by("-started_at")
            .values_list("pk", flat=True)
            .first()
        )
        deleted, _ = (
            TaskRun.objects.filter(task=task, started_at__lt=cutoff)
            .exclude(pk=most_recent_pk)
            .delete()
        )
        total_deleted += deleted

    stale_deleted, _ = TaskRun.objects.filter(
        status="PENDING", started_at__lt=pending_cutoff
    ).delete()
    total_deleted += stale_deleted

    logging.info(
        "cleanup_task_runs: deleted %d TaskRun records older than %d days, %d stale PENDING runs.",
        total_deleted - stale_deleted, days, stale_deleted,
    )

    return {"deleted": total_deleted}
