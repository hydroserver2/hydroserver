from uuid import UUID
from celery import shared_task

from processing.etl.services import EtlTaskService
from hydroserverpy.etl.exceptions import ETLError


etl_task_service = EtlTaskService()


@shared_task(bind=True, name="processing.etl.tasks.run_etl_task")
def run_etl_task(self, task_id: str):
    """
    Runs a HydroServer ETL task based on the task configuration provided.
    """

    try:
        result = etl_task_service.run(task=UUID(task_id))
    except ETLError as e:
        raise e
    except Exception as e:
        raise Exception("Encountered an unexpected ETL error.") from e

    return result
