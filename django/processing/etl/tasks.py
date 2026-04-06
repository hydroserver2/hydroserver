from uuid import UUID
from celery import shared_task

from processing.etl.services import EtlTaskService


etl_task_service = EtlTaskService()


@shared_task(bind=True, name="processing.etl.tasks.run_etl_task")
def run_etl_task(self, task_id: str, run_id: str | None = None):
    """
    Runs a HydroServer ETL task based on the task configuration provided.
    """

    return etl_task_service.run(task=UUID(task_id))
