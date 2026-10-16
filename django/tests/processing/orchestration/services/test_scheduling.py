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


@pytest.mark.parametrize("patch, every, period", [
    ({"interval": 10}, 10, "minutes"),
    ({"interval_period": "hours"}, 5, "hours"),
    ({"enabled": False}, 5, "minutes"),
    ({"crontab": None}, 5, "minutes"),
    ({}, 5, "minutes"),
])
def test_apply_schedule_preserves_omitted_members(patch, every, period):
    service = SchedulingService()
    periodic_task = service.apply_schedule(
        periodic_task=None, interval=5, interval_period="minutes",
        celery_task_name="processing.etl.tasks.run_etl_task", periodic_task_name="partial-schedule",
    )

    updated = service.apply_schedule(periodic_task=periodic_task, **patch)

    assert updated is not None
    updated.refresh_from_db()
    assert updated.interval.every == every
    assert updated.interval.period == period
    assert updated.enabled is patch.get("enabled", True)


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


@pytest.mark.parametrize("initial, patch, crontab, every", [
    ({"crontab": "0 5 * * *"}, {"interval": 10, "interval_period": "hours"}, None, 10),
    ({"interval": 5, "interval_period": "minutes"}, {"crontab": "0 6 * * *"}, "0 6 * * *", None),
])
def test_apply_schedule_switches_between_crontab_and_interval(initial, patch, crontab, every):
    service = SchedulingService()
    periodic_task = service.apply_schedule(
        periodic_task=None, **initial,
        celery_task_name="processing.etl.tasks.run_etl_task", periodic_task_name="switch-schedule",
    )

    updated = service.apply_schedule(periodic_task=periodic_task, **patch)

    updated.refresh_from_db()
    assert service.get_crontab_string(updated) == crontab
    assert (updated.interval.every if updated.interval else None) == every
