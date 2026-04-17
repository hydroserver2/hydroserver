from uuid import UUID
from celery import shared_task

from processing.products.exceptions import DataProductError
from processing.products.services import DataProductTaskService

data_products_task_service = DataProductTaskService()


@shared_task(bind=True, name="processing.products.tasks.run_data_product_task")
def run_data_product_task(self, task_id: str):
    """
    Runs a HydroServer data product task based on the task configuration provided.
    """

    try:
        result = data_products_task_service.run(task=UUID(task_id))
    except DataProductError as e:
        raise e
    except Exception as e:
        raise Exception("Encountered an unexpected data product error.") from e

    return result
