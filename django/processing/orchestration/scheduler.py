from django.conf import settings
from django_celery_beat.schedulers import DatabaseScheduler

from processing.orchestration.tracked_task import CLEANUP_TASK_NAME


class OrchestrationScheduler(DatabaseScheduler):
    """
    Stops beat from sending scheduled tasks when CELERY_ENABLED is False.

    Schedules are left untouched in the database, so they resume as they were when
    orchestration is enabled again. Task-run cleanup keeps running.
    """

    def enabled_models_qs(self):
        qs = super().enabled_models_qs()
        if not settings.CELERY_ENABLED:
            qs = qs.filter(task=CLEANUP_TASK_NAME)

        return qs
