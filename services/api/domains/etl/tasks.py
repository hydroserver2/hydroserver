from uuid import UUID
from datetime import timedelta
from celery import shared_task
from celery.signals import task_prerun, task_success, task_failure, task_postrun
from django.utils import timezone
from django.db.utils import IntegrityError
from django.core.management import call_command
from domains.etl.models import Task, TaskRun
from hydroserverpy.etl.hydroserver import build_hydroserver_pipeline
from hydroserverpy.etl.exceptions import ETLError
from .internal import HydroServerInternalExtractor, HydroServerInternalTransformer, HydroServerInternalLoader


@shared_task(bind=True, expires=10)
def run_etl_task(self, task_id: str):
    """
    Runs a HydroServer ETL task based on the task configuration provided.
    """

    try:
        task = Task.objects.select_related(
            "data_connection"
        ).prefetch_related(
            "mappings", "mappings__paths"
        ).get(pk=UUID(task_id))
    except Task.DoesNotExist as e:
        raise ETLError(
            f"ETL task with ID '{task_id}' does not exist. "
            "The task record may have been deleted before this run could execute."
        ) from e
    except Exception as e:
        raise ETLError(
            "Encountered an unexpected error while setting up the ETL task run. "
            "See task logs for additional details."
        ) from e

    # TODO: HydroServer stored settings and hydroserverpy interface should be better reconciled once automated QA/QC
    #  design is finalized.

    try:
        if task.task_type == "Aggregation":
            etl_classes = {
                "extractor_cls": HydroServerInternalExtractor,
                "transformer_cls": HydroServerInternalTransformer,
                "loader_cls": HydroServerInternalLoader
            }
        else:
            etl_classes = {
                "loader_cls": HydroServerInternalLoader
            }

        etl_pipeline, etl_data_mappings, runtime_variables = build_hydroserver_pipeline(
            task=task,
            data_connection=task.data_connection,
            data_mappings=[
                {
                    "sourceIdentifier": mapping.source_identifier,
                    "paths": [
                        {
                            "targetIdentifier": path.target_identifier,
                            "dataTransformations": path.data_transformations,
                        } for path in mapping.paths.all()
                    ]
                } for mapping in task.mappings.all()
            ],
            **etl_classes
        )
    except ETLError as e:
        raise e
    except Exception as e:
        raise ETLError(
            "Encountered an unexpected ETL configuration error. "
            "See task logs for additional details."
        ) from e

    try:
        context = etl_pipeline.run(
            task=task,
            data_mappings=etl_data_mappings,
            task_instance=task,
            raise_on_error=False,
            **runtime_variables
        )
    except Exception as e:
        raise ETLError(
            "Encountered an unexpected ETL execution error. "
            "See task logs for additional details."
        ) from e

    if context.exception:
        if isinstance(context.exception, ETLError):
            context.exception.result = {
                "runtime_variables": context.runtime_variables,
                **(context.results.dict() if context.results is not None else {})
            }
            raise context.exception
        else:
            error = ETLError(
                "Encountered an unexpected ETL execution error. "
                "See task logs for additional details."
            )
            error.results = context.results.dict()
            raise error from context.exception

    if context.results.values_loaded_total == 0:
        message = "Already up-to-date. No new observations were loaded."
    else:
        message = (
            f"Loaded {context.results.values_loaded_total} total observation(s) "
            f"into {context.results.success_count} datastream(s)."
        )

    return {
        "message": message,
        "runtime_variables": context.runtime_variables,
        **context.results.dict(),
    }


@task_prerun.connect
def mark_etl_task_started(sender, task_id, kwargs, **extra):
    """
    Marks an ETL task as RUNNING.
    """

    if sender != run_etl_task:
        return

    try:
        TaskRun.objects.create(
            id=task_id,
            task_id=kwargs["task_id"],
            status="RUNNING",
            started_at=timezone.now(),
        )
    except IntegrityError:
        return


@task_postrun.connect
def update_next_run(sender, task_id, kwargs, **extra):
    if sender != run_etl_task:
        return

    try:
        task = Task.objects.select_related("periodic_task").get(
            pk=kwargs["task_id"]
        )
    except Task.DoesNotExist:
        return

    if not task.periodic_task:
        task.next_run_at = None
        task.save(update_fields=["next_run_at"])
        return

    now = timezone.now()

    time_delta = task.periodic_task.schedule.remaining_estimate(now)
    time_delta = max(time_delta, timedelta(0))

    task.next_run_at = now + time_delta
    task.save(update_fields=["next_run_at"])


@task_success.connect
def mark_etl_task_success(sender, result, **extra):
    """
    Marks an ETL task as SUCCESS.
    """

    if sender != run_etl_task:
        return

    try:
        task_run = TaskRun.objects.get(id=sender.request.id)
    except TaskRun.DoesNotExist:
        return

    task_run.status = "SUCCESS"
    task_run.finished_at = timezone.now()
    task_run.result = result

    task_run.save(update_fields=["status", "finished_at", "result"])


@task_failure.connect
def mark_etl_task_failure(sender, task_id, einfo, exception, **extra):
    """
    Marks an ETL task as FAILED.
    """

    if sender != run_etl_task:
        return

    try:
        task_run = TaskRun.objects.get(id=task_id)
    except TaskRun.DoesNotExist:
        return

    task_run.status = "FAILURE"
    task_run.finished_at = timezone.now()
    task_run.result = {
        "error": str(exception),
        "traceback": einfo.traceback,
        **(getattr(exception, "results", None) or {}),
    }

    task_run.save(update_fields=["status", "finished_at", "result"])


@shared_task(bind=True, expires=10)
def cleanup_etl_task_runs(self, days=14):
    """
    Celery task to run the cleanup_etl_task_runs management command.
    """

    call_command("cleanup_etl_task_runs", f"--days={days}")
