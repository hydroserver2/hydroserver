import logging
from uuid import UUID
from datetime import timedelta
from celery import shared_task
from celery.signals import task_prerun, task_success, task_failure, task_postrun
from django.utils import timezone
from django.utils.html import strip_tags
from django.db.models import Prefetch
from django.db.utils import IntegrityError
from django.core.management import call_command
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from processing.etl.models import Task, TaskRun, DataConnection
from core.sta.models import Datastream
from hydroserverpy.etl.hydroserver import build_hydroserver_pipeline
from hydroserverpy.etl.exceptions import ETLError
from .internal import HydroServerInternalExtractor, HydroServerInternalTransformer, HydroServerInternalLoader


def _serialize_log_entries(context) -> list[dict]:
    entries = getattr(context, "log_entries", None) or []
    serialized = []

    for entry in entries:
        if hasattr(entry, "model_dump"):
            serialized.append(entry.model_dump(mode="json"))
        elif isinstance(entry, dict):
            serialized.append(entry)

    return serialized


def _build_context_result_payload(context) -> dict:
    payload = {
        "runtime_variables": context.runtime_variables,
        "log_entries": _serialize_log_entries(context),
    }

    if context.results is not None:
        payload.update(context.results.dict())

    return payload


def _raise_aggregation_error(message: str):
    raise ETLError(message)


def _validate_aggregation_task_runtime(task: Task):
    mappings = list(task.mappings.all())
    if not mappings:
        _raise_aggregation_error("Aggregation tasks must include at least one mapping.")

    datastream_ids = set()
    for mapping in mappings:
        try:
            datastream_ids.add(UUID(str(mapping.source_identifier)))
        except (TypeError, ValueError):
            _raise_aggregation_error(
                "Aggregation mapping sourceIdentifier must be a valid datastream UUID."
            )

        paths = list(mapping.paths.all())
        if len(paths) != 1:
            _raise_aggregation_error(
                "Aggregation mappings must include exactly one target path per source."
            )

        path = paths[0]
        transformations = path.data_transformations or []
        if (
            not isinstance(transformations, list)
            or len(transformations) != 1
            or not isinstance(transformations[0], dict)
            or transformations[0].get("type") != "aggregation"
        ):
            _raise_aggregation_error(
                "Aggregation mappings must include exactly one aggregation transformation per path."
            )

        try:
            datastream_ids.add(UUID(str(path.target_identifier)))
        except (TypeError, ValueError):
            _raise_aggregation_error(
                "Aggregation mapping targetIdentifier must be a valid datastream UUID."
            )

    existing_datastream_ids = set(
        Datastream.objects.filter(
            thing__workspace_id=task.workspace_id,
            id__in=datastream_ids,
        ).values_list("id", flat=True)
    )
    if datastream_ids - existing_datastream_ids:
        _raise_aggregation_error(
            "Aggregation source and target datastreams must exist in the task workspace."
        )


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
            _validate_aggregation_task_runtime(task)
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
            context.exception.result = _build_context_result_payload(context)
            context.exception.results = context.exception.result
            raise context.exception
        else:
            error = ETLError(
                "Encountered an unexpected ETL execution error. "
                "See task logs for additional details."
            )
            error.results = _build_context_result_payload(context)
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
        **_build_context_result_payload(context),
    }


@task_prerun.connect
def mark_etl_task_started(sender, task_id, kwargs, **extra):
    """
    Marks an ETL task as RUNNING.
    """

    if sender != run_etl_task:
        return

    try:
        TaskRun.objects.update_or_create(
            id=task_id,
            defaults={
                "task_id": kwargs["task_id"],
                "status": "RUNNING",
                "started_at": timezone.now(),
                "finished_at": None,
                "result": None,
            },
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

    result = {
        "message": str(exception),
        "error": str(exception),
        "traceback": einfo.traceback,
    }
    result.update(
        getattr(exception, "results", None)
        or getattr(exception, "result", None)
        or {}
    )

    task_run.status = "FAILURE"
    task_run.finished_at = timezone.now()
    task_run.result = result

    task_run.save(update_fields=["status", "finished_at", "result"])


@shared_task(bind=True, expires=10)
def cleanup_etl_task_runs(self, days=14):
    """
    Celery task to run the cleanup_etl_task_runs management command.
    """

    call_command("cleanup_etl_task_runs", f"--days={days}")


@shared_task(bind=True, expires=10)
def send_orchestration_notifications(self):
    """
    Celery task to run the send_orchestration_notifications management command.
    """

    task_run_queryset = TaskRun.objects.filter(
        started_at__gte=timezone.now() - timedelta(days=1)
    ).order_by("-started_at")

    data_connections = DataConnection.objects.prefetch_related(
        "notification_recipients", "tasks", Prefetch(
            "tasks__taskrun_set",
            queryset=task_run_queryset,
            to_attr="daily_task_runs",
        ),
    ).all()

    for data_connection in data_connections:
        subject = f"Job Orchestration Status: {data_connection.name}"
        recipients = [
            notification_recipient.email
            for notification_recipient in data_connection.notification_recipients.all()
        ]

        task_summaries = []

        for task in data_connection.tasks.all():
            task_summaries.append({
                "id": task.id,
                "name": task.name,
                "run_count": len(task.daily_task_runs),
                "failure_count": sum(1 for run in task.daily_task_runs if run.status == "FAILURE"),
                "last_run_message": task.daily_task_runs[0].result.get("message", "") if task.daily_task_runs else "",
                "link": f"{settings.PROXY_BASE_URL}/orchestration?taskId={task.id}"
            })

        if not task_summaries:
            logging.info(
                "Skipping email for DataConnection %s because there are no tasks today.",
                data_connection.name
            )
            continue

        if not recipients:
            logging.info(
                "Skipping email for DataConnection %s because there are no notification recipients.",
                data_connection.name
            )
            continue

        context = {
            "data_connection_name": data_connection.name,
            "tasks": task_summaries
        }

        html_content = render_to_string("orchestration/email/orchestration_notification.html", context)
        text_content = strip_tags(html_content)

        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=None,
                to=recipients,
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)

            logging.info(
                "Sent orchestration summary email for DataConnection %s to: %s",
                data_connection.name,
                recipients
            )

        except Exception as e:
            logging.error(
                "Failed to send email for DataConnection %s to %s: %s",
                data_connection.name,
                recipients,
                str(e),
                exc_info=True
            )
