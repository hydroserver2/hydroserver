from hydroserver.celery import app as celery_app
from interfaces.api.services.etl import data_connection, task as etl_task
from interfaces.api.services.monitoring import task as monitoring_task
from interfaces.api.services.products import task as products_task


def test_scheduled_celery_task_names_are_registered():
    celery_app.loader.import_default_modules()

    assert {
        etl_task.CELERY_TASK_NAME,
        data_connection.ETL_NOTIFICATION_CELERY_TASK,
        monitoring_task.CELERY_TASK_NAME,
        products_task.CELERY_TASK_NAME,
    } <= set(celery_app.tasks)
