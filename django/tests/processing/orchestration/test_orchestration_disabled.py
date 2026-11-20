import json

import pytest
from celery import states
from django.test import override_settings
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from hydroserver.celery import app as celery_app
from interfaces.api.services.etl import task as etl_task
from processing.orchestration.models import TaskRun
from processing.orchestration.scheduler import OrchestrationScheduler
from processing.orchestration.tracked_task import CLEANUP_TASK_NAME
from tests.processing.etl.factories import EtlTaskFactory

pytestmark = pytest.mark.django_db


def _periodic_task(name, task):
    interval, _ = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.HOURS)
    return PeriodicTask.objects.create(name=name, task=task, interval=interval, enabled=True)


def _scheduled_task_names():
    scheduler = OrchestrationScheduler(app=celery_app, lazy=True)
    return set(scheduler.enabled_models_qs().values_list("task", flat=True))


# --- worker guard -------------------------------------------------------------------------


@override_settings(CELERY_ENABLED=False)
def test_worker_skips_hydroserver_task_without_recording_run_when_disabled():
    celery_app.loader.import_default_modules()
    task = EtlTaskFactory()

    result = celery_app.tasks[etl_task.CELERY_TASK_NAME].apply(kwargs={"task_id": str(task.id)})

    assert result.state == states.IGNORED
    assert not TaskRun.objects.filter(task=task).exists()


@override_settings(CELERY_ENABLED=False)
def test_worker_still_runs_task_run_cleanup_when_disabled():
    celery_app.loader.import_default_modules()

    result = celery_app.tasks[CLEANUP_TASK_NAME].apply(kwargs={"days": 7})

    assert result.state == states.SUCCESS


# --- scheduler guard ----------------------------------------------------------------------


def test_scheduler_sends_all_enabled_schedules_when_enabled():
    _periodic_task("etl", etl_task.CELERY_TASK_NAME)
    _periodic_task("cleanup", CLEANUP_TASK_NAME)

    assert {etl_task.CELERY_TASK_NAME, CLEANUP_TASK_NAME} <= _scheduled_task_names()


@override_settings(CELERY_ENABLED=False)
def test_scheduler_only_sends_cleanup_when_disabled():
    etl = _periodic_task("etl", etl_task.CELERY_TASK_NAME)
    _periodic_task("cleanup", CLEANUP_TASK_NAME)

    assert _scheduled_task_names() == {CLEANUP_TASK_NAME}

    # Schedules are left as they were, so they resume when orchestration is re-enabled.
    etl.refresh_from_db()
    assert etl.enabled
    assert json.loads(etl.kwargs) == {}
