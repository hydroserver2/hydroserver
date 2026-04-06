from celery import shared_task


@shared_task(bind=True, name="processing.monitoring.tasks.run_monitoring_task")
def run_monitoring_task(self, task_id: str, run_id: str | None = None):
    """
    Runs a HydroServer monitoring task based on the task configuration provided.
    """

    raise NotImplementedError("Monitoring task executor is not yet implemented.")
