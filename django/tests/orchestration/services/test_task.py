import uuid
import pytest
from django.utils import timezone
from processing.orchestration.models import Task, TaskRun
from processing.orchestration.services.task import TaskService
from processing.etl.models import EtlTask
from processing.etl.services.task import EtlTaskService

TASK_ID = uuid.UUID("019adbc3-35e8-7f25-bc68-171fb66d446e")
TASK_RUN_ID = uuid.UUID("019adb60-8cb6-70cc-a1b1-91c2f0ded756")
CRONTAB_DAILY = "0 8 * * *"

etl_task_service = EtlTaskService()


# --- annotate_latest_run ---

def test_annotate_latest_run_populates_fields():
    qs = TaskService.annotate_latest_run(EtlTask.objects.filter(pk=TASK_ID))
    task = qs.get()

    assert task.latest_run_id == TASK_RUN_ID
    assert task.latest_run_status == "SUCCESS"
    assert task.latest_run_started_at is not None
    assert task.latest_run_finished_at is not None


def test_annotate_latest_run_includes_message_and_result():
    qs = TaskService.annotate_latest_run(EtlTask.objects.filter(pk=TASK_ID))
    task = qs.get()

    assert task.latest_run_message == "OK"
    assert task.latest_run_result is None


def test_annotate_latest_run_is_none_when_no_runs():
    task = Task.objects.create(name="No-run Task")
    qs = TaskService.annotate_latest_run(Task.objects.filter(pk=task.pk))
    annotated = qs.get()

    assert annotated.latest_run_id is None
    assert annotated.latest_run_status is None
    assert annotated.latest_run_started_at is None
    assert annotated.latest_run_finished_at is None


def test_annotate_latest_run_returns_most_recent():
    task = Task.objects.create(name="Multi-run Task")
    TaskRun.objects.create(task=task, status="FAILURE")
    latest_run = TaskRun.objects.create(task=task, status="SUCCESS")

    qs = TaskService.annotate_latest_run(Task.objects.filter(pk=task.pk))
    annotated = qs.get()

    assert annotated.latest_run_id == latest_run.id
    assert annotated.latest_run_status == "SUCCESS"


# --- get_run_collection ---

def test_get_run_collection_returns_runs():
    count, runs = etl_task_service.get_run_collection(task=TASK_ID)

    assert count == 1
    run = list(runs)[0]
    assert run.id == TASK_RUN_ID
    assert run.status == "SUCCESS"


def test_get_run_collection_filters_by_status():
    count_success, _ = etl_task_service.get_run_collection(task=TASK_ID, status=["SUCCESS"])
    count_failure, _ = etl_task_service.get_run_collection(task=TASK_ID, status=["FAILURE"])

    assert count_success == 1
    assert count_failure == 0


def test_get_run_collection_pagination():
    task = Task.objects.get(pk=TASK_ID)
    for _ in range(5):
        TaskRun.objects.create(task=task, status="SUCCESS")

    count, runs_page1 = etl_task_service.get_run_collection(task=TASK_ID, page=1, page_size=3)
    count, runs_page2 = etl_task_service.get_run_collection(task=TASK_ID, page=2, page_size=3)

    assert count == 6  # 1 from fixture + 5 created
    assert len(list(runs_page1)) == 3
    assert len(list(runs_page2)) == 3


def test_get_run_collection_empty_page():
    count, runs = etl_task_service.get_run_collection(task=TASK_ID, page=2, page_size=100)

    assert count == 1
    assert len(list(runs)) == 0


# --- apply_schedule (TaskService wrapper) ---

def test_task_apply_schedule_sets_crontab():
    task = etl_task_service.apply_schedule(task=TASK_ID, crontab=CRONTAB_DAILY, enabled=True)

    assert task.periodic_task is not None
    assert task.periodic_task.crontab is not None
    assert task.periodic_task.crontab.hour == "8"
    assert task.next_run_at is not None
    assert task.next_run_at > timezone.now()


def test_task_apply_schedule_clears_schedule():
    task = etl_task_service.apply_schedule(task=TASK_ID, crontab=None)

    assert task.periodic_task is None
    task.refresh_from_db()
    assert task.periodic_task is None


def test_task_apply_schedule_clears_next_run_at_when_schedule_removed():
    etl_task = EtlTask.objects.get(pk=TASK_ID)
    etl_task.next_run_at = timezone.now()
    etl_task.save()

    task = etl_task_service.apply_schedule(task=TASK_ID, crontab=None)

    assert task.next_run_at is None


def test_task_apply_schedule_sets_next_run_at_when_enabled():
    task = etl_task_service.apply_schedule(task=TASK_ID, crontab=CRONTAB_DAILY, enabled=False)
    assert task.next_run_at is None

    task = etl_task_service.apply_schedule(task=TASK_ID, enabled=True)
    assert task.next_run_at is not None
    assert task.next_run_at > timezone.now()
