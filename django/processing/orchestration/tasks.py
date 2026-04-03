import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from processing.orchestration.models import Task, TaskRun


@shared_task(bind=True, expires=10)
def cleanup_task_runs(self, days=14):
    """
    Delete TaskRun records older than `days` days, keeping the most recent
    run per task regardless of age.
    """

    cutoff = timezone.now() - timedelta(days=days)
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

    logging.info("cleanup_task_runs: deleted %d TaskRun records older than %d days.", total_deleted, days)

    return {"deleted": total_deleted}