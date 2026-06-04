from celery import Task
from django.utils import timezone

from processing.orchestration.logging import RunIdFilter, run_id_var


class TrackedTask(Task):
    """
    Abstract Celery task base class that automatically manages the TaskRun lifecycle.
    """

    abstract = True

    task_id_kwarg = "task_id"
    run_id_kwarg = "run_id"

    default_success_message = "Task completed successfully."
    default_failure_message = "Task failed."

    run_id_filter = RunIdFilter()

    def _get_or_create_run(self, kwargs: dict) -> str | None:
        """
        Return the run_id to track for this execution.
        """

        from processing.orchestration.models import TaskRun

        run_id = kwargs.get(self.run_id_kwarg)
        hs_task_id = kwargs.get(self.task_id_kwarg)

        if run_id:
            TaskRun.objects.filter(pk=run_id).update(status="STARTED")

            return run_id

        if hs_task_id:
            run = TaskRun.objects.create(task_id=hs_task_id, status="STARTED")

            return str(run.id)

        return None

    def before_start(self, task_id, args, kwargs):
        self.request.tracking_run_id = self._get_or_create_run(kwargs)
        run_id_var.set(self.request.tracking_run_id or "-")

    def on_success(self, retval, task_id, args, kwargs):
        from processing.orchestration.models import TaskRun

        run_id = getattr(self.request, "tracking_run_id", None)

        if not run_id:
            return

        result = dict(retval) if isinstance(retval, dict) else {}
        message = result.pop("message", self.default_success_message)

        TaskRun.objects.filter(pk=run_id).update(
            status="SUCCESS",
            message=message,
            result=result or None,
            finished_at=timezone.now(),
        )

        run_id_var.set("-")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        from processing.orchestration.models import TaskRun

        run_id = getattr(self.request, "tracking_run_id", None)

        if not run_id:
            return

        result = getattr(exc, "result", None) or None
        message = str(exc) or self.default_failure_message

        TaskRun.objects.filter(pk=run_id).update(
            status="FAILURE",
            message=message,
            result=result,
            finished_at=timezone.now(),
        )

        run_id_var.set("-")

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        hs_task_id = kwargs.get(self.task_id_kwarg)

        if not hs_task_id:
            return

        from processing.orchestration.models import Task
        from processing.orchestration.services.scheduling import SchedulingService

        try:
            task = Task.objects.select_related(
                "periodic_task",
                "periodic_task__crontab",
                "periodic_task__interval",
            ).get(pk=hs_task_id)
        except Task.DoesNotExist:
            return

        task.next_run_at = SchedulingService.compute_next_run_at(task.periodic_task)
        task.save(update_fields=["next_run_at"])
