from datetime import datetime, timedelta, timezone as dt_timezone
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from django_celery_beat.models import PeriodicTask

from processing.orchestration.services.scheduling import SchedulingService

pytestmark = pytest.mark.django_db


def test_apply_schedule_creates_crontab_schedule():
    periodic_task = SchedulingService().apply_schedule(
        periodic_task=None,
        crontab="0 5 * * *",
        celery_task_name="processing.etl.tasks.run_etl_task",
        periodic_task_name="test-crontab-schedule",
    )

    assert isinstance(periodic_task, PeriodicTask)
    assert periodic_task.crontab.minute == "0"
    assert periodic_task.crontab.hour == "5"
    assert periodic_task.crontab.day_of_month == "*"
    assert periodic_task.crontab.month_of_year == "*"
    assert periodic_task.crontab.day_of_week == "*"
    assert periodic_task.interval is None


def test_apply_schedule_rejects_invalid_crontab_field_value():
    with pytest.raises(ValidationError):
        SchedulingService().apply_schedule(
            periodic_task=None,
            crontab="99 5 * * *",
            celery_task_name="processing.etl.tasks.run_etl_task",
            periodic_task_name="test-invalid-crontab",
        )


def test_apply_schedule_creates_interval_schedule():
    periodic_task = SchedulingService().apply_schedule(
        periodic_task=None,
        interval=5,
        interval_period="minutes",
        celery_task_name="processing.etl.tasks.run_etl_task",
        periodic_task_name="test-interval-schedule",
    )

    assert isinstance(periodic_task, PeriodicTask)
    assert periodic_task.interval.every == 5
    assert periodic_task.interval.period == "minutes"
    assert periodic_task.crontab is None


def test_apply_schedule_rejects_interval_less_than_one():
    with pytest.raises(ValidationError):
        SchedulingService().apply_schedule(
            periodic_task=None,
            interval=0,
            interval_period="minutes",
            celery_task_name="processing.etl.tasks.run_etl_task",
            periodic_task_name="test-interval-too-small",
        )


def test_apply_schedule_rejects_missing_interval_period():
    with pytest.raises(ValidationError):
        SchedulingService().apply_schedule(
            periodic_task=None,
            interval=5,
            celery_task_name="processing.etl.tasks.run_etl_task",
            periodic_task_name="test-missing-interval-period",
        )


def test_apply_schedule_rejects_both_crontab_and_interval():
    with pytest.raises(ValidationError):
        SchedulingService().apply_schedule(
            periodic_task=None,
            crontab="0 5 * * *",
            interval=5,
            interval_period="minutes",
            celery_task_name="processing.etl.tasks.run_etl_task",
            periodic_task_name="test-both-crontab-and-interval",
        )


def test_compute_previous_run_at_returns_run_before_current_crontab_run():
    periodic_task = SchedulingService().apply_schedule(
        periodic_task=None,
        crontab="0 9 * * *",
        celery_task_name="processing.etl.tasks.send_etl_notification_email",
        periodic_task_name="test-previous-crontab",
    )

    with mock.patch("django.utils.timezone.now", return_value=datetime(2026, 1, 2, 9, 0, 5, tzinfo=dt_timezone.utc)):
        previous = SchedulingService.compute_previous_run_at(periodic_task)

    assert previous == datetime(2026, 1, 1, 9, 0, tzinfo=dt_timezone.utc)


def test_compute_previous_run_at_subtracts_interval():
    periodic_task = SchedulingService().apply_schedule(
        periodic_task=None,
        interval=6,
        interval_period="hours",
        celery_task_name="processing.etl.tasks.send_etl_notification_email",
        periodic_task_name="test-previous-interval",
    )
    now = datetime(2026, 1, 2, 9, 0, tzinfo=dt_timezone.utc)

    with mock.patch("django.utils.timezone.now", return_value=now):
        previous = SchedulingService.compute_previous_run_at(periodic_task)

    assert previous == now - timedelta(hours=6)
