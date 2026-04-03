from celery import shared_task


@shared_task(bind=True, name="processing.etl.tasks.run_etl_task")
def run_etl_task(self, task_id: str):
    """
    Execute an ETL task identified by the given orchestration Task ID.
    """

    raise NotImplementedError("ETL task runner is not yet implemented.")
