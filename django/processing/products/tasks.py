from celery import shared_task


@shared_task(bind=True, name="processing.products.tasks.run_data_product_task")
def run_data_product_task(self, task_id: str, run_id: str | None = None):
    """
    Runs a HydroServer data product task based on the task configuration provided.
    """

    raise NotImplementedError("Data product task executor is not yet implemented.")
