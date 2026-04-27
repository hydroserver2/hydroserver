from uuid import UUID
from celery import shared_task

from processing.monitoring.exceptions import MonitoringError
from processing.monitoring.services import MonitoringTaskService

monitoring_task_service = MonitoringTaskService()


@shared_task(bind=True, name="processing.monitoring.tasks.run_monitoring_task")
def run_monitoring_task(self, task_id: str, run_id: str | None = None):
    """
    Runs a HydroServer monitoring task based on the task configuration provided.
    """

    try:
        result = monitoring_task_service.run(task=UUID(task_id))
    except MonitoringError as e:
        raise e
    except Exception as e:
        raise Exception("Encountered an unexpected data monitoring error.") from e

    return result
