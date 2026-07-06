import uuid
import pytest
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask
from processing.orchestration.services.scheduling import SchedulingService

CELERY_TASK = "my.celery.task"
CRONTAB_DAILY = "0 8 * * *"
CRONTAB_WEEKLY = "0 9 * * 1"

service = SchedulingService()


# --- apply_schedule: create new ---

def test_apply_schedule_creates_crontab():
    pt = service.apply_schedule(
        periodic_task=None,
        crontab=CRONTAB_DAILY,
        celery_task_name=CELERY_TASK,
    )
    assert pt is not None
    assert pt.task == CELERY_TASK
    assert pt.crontab is not None
    assert pt.crontab.minute == "0"
    assert pt.crontab.hour == "8"
    assert pt.crontab.day_of_month == "*"
    assert pt.crontab.month_of_year == "*"
    assert pt.crontab.day_of_week == "*"
    assert pt.interval is None
    assert pt.enabled is True


def test_apply_schedule_creates_interval():
    pt = service.apply_schedule(
        periodic_task=None,
        interval=6,
        interval_period="hours",
        celery_task_name=CELERY_TASK,
    )
    assert pt is not None
    assert pt.interval is not None
    assert pt.interval.every == 6
    assert pt.interval.period == "hours"
    assert pt.crontab is None


def test_apply_schedule_create_disabled():
    pt = service.apply_schedule(
        periodic_task=None,
        crontab=CRONTAB_DAILY,
        celery_task_name=CELERY_TASK,
        enabled=False,
    )
    assert pt.enabled is False


def test_apply_schedule_stores_kwargs():
    task_id = str(uuid.uuid4())
    pt = service.apply_schedule(
        periodic_task=None,
        crontab=CRONTAB_DAILY,
        celery_task_name=CELERY_TASK,
        celery_task_kwargs={"task_id": task_id},
    )
    assert task_id in pt.kwargs


def test_apply_schedule_no_schedule_returns_none():
    result = service.apply_schedule(periodic_task=None)
    assert result is None


# --- apply_schedule: update existing ---

def test_apply_schedule_updates_existing_crontab():
    pt = service.apply_schedule(
        periodic_task=None, crontab=CRONTAB_DAILY, celery_task_name=CELERY_TASK
    )
    original_crontab_pk = pt.crontab.pk

    updated = service.apply_schedule(periodic_task=pt, crontab=CRONTAB_WEEKLY)

    assert updated.pk == pt.pk
    assert updated.crontab.pk == original_crontab_pk  # row reused, not recreated
    assert updated.crontab.hour == "9"
    assert updated.crontab.day_of_week == "1"


def test_apply_schedule_switches_crontab_to_interval():
    pt = service.apply_schedule(
        periodic_task=None, crontab=CRONTAB_DAILY, celery_task_name=CELERY_TASK
    )
    old_crontab_pk = pt.crontab.pk

    updated = service.apply_schedule(periodic_task=pt, interval=2, interval_period="days")

    assert updated.crontab is None
    assert updated.interval is not None
    assert updated.interval.every == 2
    assert not CrontabSchedule.objects.filter(pk=old_crontab_pk).exists()


def test_apply_schedule_updates_existing_interval_count():
    pt = service.apply_schedule(
        periodic_task=None, interval=5, interval_period="hours", celery_task_name=CELERY_TASK
    )
    updated = service.apply_schedule(periodic_task=pt, interval=10, interval_period="hours")

    assert updated.interval.every == 10
    assert updated.interval.period == "hours"


def test_apply_schedule_updates_existing_interval_period():
    pt = service.apply_schedule(
        periodic_task=None, interval=5, interval_period="hours", celery_task_name=CELERY_TASK
    )
    updated = service.apply_schedule(periodic_task=pt, interval=5, interval_period="days")

    assert updated.interval.every == 5
    assert updated.interval.period == "days"


def test_apply_schedule_switches_interval_to_crontab():
    pt = service.apply_schedule(
        periodic_task=None, interval=3, interval_period="hours", celery_task_name=CELERY_TASK
    )
    old_interval_pk = pt.interval.pk

    updated = service.apply_schedule(periodic_task=pt, crontab=CRONTAB_DAILY)

    assert updated.interval is None
    assert updated.crontab is not None
    assert updated.crontab.hour == "8"
    assert not IntervalSchedule.objects.filter(pk=old_interval_pk).exists()


def test_apply_schedule_clears_schedule_with_crontab_none():
    pt = service.apply_schedule(
        periodic_task=None, crontab=CRONTAB_DAILY, celery_task_name=CELERY_TASK
    )
    pt_pk = pt.pk

    result = service.apply_schedule(periodic_task=pt, crontab=None)

    assert result is None
    assert not PeriodicTask.objects.filter(pk=pt_pk).exists()


def test_apply_schedule_updates_enabled():
    pt = service.apply_schedule(
        periodic_task=None,
        crontab=CRONTAB_DAILY,
        celery_task_name=CELERY_TASK,
        enabled=False,
    )
    updated = service.apply_schedule(periodic_task=pt, enabled=True)
    assert updated.enabled is True


# --- apply_schedule: last_run_at on start_time update ---

def test_apply_schedule_update_past_start_time_realigns_last_run_at():
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        pt = service.apply_schedule(
            periodic_task=None, interval=6, interval_period="hours",
            celery_task_name=CELERY_TASK,
        )

    new_start = FIXED_NOW - timedelta(hours=3)
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        updated = service.apply_schedule(periodic_task=pt, start_time=new_start)

    assert updated.last_run_at == new_start


def test_apply_schedule_update_future_start_time_clears_last_run_at():
    past_start = FIXED_NOW - timedelta(hours=5)
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        pt = service.apply_schedule(
            periodic_task=None, interval=6, interval_period="hours",
            celery_task_name=CELERY_TASK, start_time=past_start,
        )

    future_start = FIXED_NOW + timedelta(hours=2)
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        updated = service.apply_schedule(periodic_task=pt, start_time=future_start)

    assert updated.last_run_at is None


# --- apply_schedule: last_run_at on creation ---

def test_apply_schedule_interval_past_start_sets_last_run_at():
    past_start = FIXED_NOW - timedelta(hours=2)
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        pt = service.apply_schedule(
            periodic_task=None, interval=6, interval_period="hours",
            celery_task_name=CELERY_TASK, start_time=past_start,
        )
    # elapsed=2h < delta=6h → n=0 → last_run_at = past_start
    assert pt.last_run_at == past_start


def test_apply_schedule_interval_past_start_anchors_to_last_occurrence():
    past_start = FIXED_NOW - timedelta(hours=14)
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        pt = service.apply_schedule(
            periodic_task=None, interval=6, interval_period="hours",
            celery_task_name=CELERY_TASK, start_time=past_start,
        )
    # elapsed=14h, delta=6h → n=2 → last_run_at = past_start + 12h
    assert pt.last_run_at == past_start + timedelta(hours=12)


def test_apply_schedule_crontab_past_start_sets_last_run_at_to_now():
    past_start = FIXED_NOW - timedelta(days=1)
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        pt = service.apply_schedule(
            periodic_task=None, crontab=CRONTAB_DAILY,
            celery_task_name=CELERY_TASK, start_time=past_start,
        )
    assert pt.last_run_at == FIXED_NOW


def test_apply_schedule_future_start_leaves_last_run_at_null():
    future_start = FIXED_NOW + timedelta(hours=2)
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        pt = service.apply_schedule(
            periodic_task=None, interval=1, interval_period="hours",
            celery_task_name=CELERY_TASK, start_time=future_start,
        )
    assert pt.last_run_at is None


# --- apply_schedule: validation errors ---

@pytest.mark.parametrize("extra_kwargs, error_message", [
    (
        {"crontab": CRONTAB_DAILY, "interval": 1, "interval_period": "hours"},
        "Only one",
    ),
    (
        {"crontab": "not a valid crontab"},
        "Invalid crontab",
    ),
    (
        {"interval": 0, "interval_period": "hours"},
        "at least 1",
    ),
    (
        {"interval": 1},
        "interval_period is required",
    ),
])
def test_apply_schedule_raises_on_invalid_input(transactional_db, extra_kwargs, error_message):
    with pytest.raises(ValueError, match=error_message):
        service.apply_schedule(
            periodic_task=None, celery_task_name=CELERY_TASK, **extra_kwargs
        )


def test_apply_schedule_raises_without_celery_task_name():
    with pytest.raises(ValueError, match="celery_task_name is required"):
        service.apply_schedule(periodic_task=None, crontab=CRONTAB_DAILY)


# --- delete_schedule ---

def test_delete_schedule_removes_crontab_and_periodic_task():
    pt = service.apply_schedule(
        periodic_task=None, crontab=CRONTAB_DAILY, celery_task_name=CELERY_TASK
    )
    pt_pk = pt.pk
    crontab_pk = pt.crontab.pk

    service.delete_schedule(pt)

    assert not PeriodicTask.objects.filter(pk=pt_pk).exists()
    assert not CrontabSchedule.objects.filter(pk=crontab_pk).exists()


def test_delete_schedule_removes_interval_and_periodic_task():
    pt = service.apply_schedule(
        periodic_task=None, interval=1, interval_period="days", celery_task_name=CELERY_TASK
    )
    pt_pk = pt.pk
    interval_pk = pt.interval.pk

    service.delete_schedule(pt)

    assert not PeriodicTask.objects.filter(pk=pt_pk).exists()
    assert not IntervalSchedule.objects.filter(pk=interval_pk).exists()


# --- get_crontab_string ---

def test_get_crontab_string_returns_expression():
    pt = service.apply_schedule(
        periodic_task=None, crontab="30 6 * * 1", celery_task_name=CELERY_TASK
    )
    assert SchedulingService.get_crontab_string(pt) == "30 6 * * 1"


def test_get_crontab_string_returns_none_for_interval():
    pt = service.apply_schedule(
        periodic_task=None, interval=1, interval_period="hours", celery_task_name=CELERY_TASK
    )
    assert SchedulingService.get_crontab_string(pt) is None


# --- compute_next_run_at ---

FIXED_NOW = datetime(2026, 5, 21, 10, 0, 0, tzinfo=dt_timezone.utc)


def test_compute_next_run_at_returns_none_for_no_periodic_task():
    assert SchedulingService.compute_next_run_at(None) is None


def test_compute_next_run_at_returns_none_when_disabled():
    pt = service.apply_schedule(
        periodic_task=None,
        crontab="0 12 * * *",
        celery_task_name=CELERY_TASK,
        enabled=False,
    )
    assert SchedulingService.compute_next_run_at(pt) is None


def test_compute_next_run_at_crontab_returns_next_match():
    pt = service.apply_schedule(
        periodic_task=None, crontab="0 12 * * *", celery_task_name=CELERY_TASK
    )
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        result = SchedulingService.compute_next_run_at(pt)

    assert result is not None
    assert result.tzinfo is not None
    assert result > FIXED_NOW
    assert result.hour == 12
    assert result.minute == 0


def test_compute_next_run_at_crontab_future_start_time():
    future_start = FIXED_NOW + timedelta(days=3)
    pt = service.apply_schedule(
        periodic_task=None,
        crontab="0 12 * * *",
        celery_task_name=CELERY_TASK,
        start_time=future_start,
    )
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        result = SchedulingService.compute_next_run_at(pt)

    assert result is not None
    assert result >= future_start
    assert result.hour == 12
    assert result.minute == 0


def test_compute_next_run_at_interval_minutes():
    # 1h past start with 30min interval → n=2, last_run_at=FIXED_NOW → next = FIXED_NOW+30min
    past_start = FIXED_NOW - timedelta(hours=1)
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        pt = service.apply_schedule(
            periodic_task=None, interval=30, interval_period="minutes",
            celery_task_name=CELERY_TASK, start_time=past_start,
        )
        result = SchedulingService.compute_next_run_at(pt)

    assert result == FIXED_NOW + timedelta(minutes=30)


def test_compute_next_run_at_interval_hours():
    # 1h past start with 6h interval → n=0, last_run_at=past_start → next = past_start+6h
    past_start = FIXED_NOW - timedelta(hours=1)
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        pt = service.apply_schedule(
            periodic_task=None, interval=6, interval_period="hours",
            celery_task_name=CELERY_TASK, start_time=past_start,
        )
        result = SchedulingService.compute_next_run_at(pt)

    assert result == past_start + timedelta(hours=6)


def test_compute_next_run_at_interval_days():
    # 1h past start with 1-day interval → n=0, last_run_at=past_start → next = past_start+1day
    past_start = FIXED_NOW - timedelta(hours=1)
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        pt = service.apply_schedule(
            periodic_task=None, interval=1, interval_period="days",
            celery_task_name=CELERY_TASK, start_time=past_start,
        )
        result = SchedulingService.compute_next_run_at(pt)

    assert result == past_start + timedelta(days=1)


def test_compute_next_run_at_interval_uses_last_run_at():
    past_start = FIXED_NOW - timedelta(hours=5)
    pt = service.apply_schedule(
        periodic_task=None, interval=6, interval_period="hours",
        celery_task_name=CELERY_TASK, start_time=past_start,
    )
    last_run = FIXED_NOW - timedelta(hours=2)
    pt.last_run_at = last_run
    pt.save()

    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        result = SchedulingService.compute_next_run_at(pt)

    assert result == last_run + timedelta(hours=6)


def test_compute_next_run_at_interval_overdue_schedules_one_interval_from_now():
    past_start = FIXED_NOW - timedelta(hours=10)
    pt = service.apply_schedule(
        periodic_task=None, interval=6, interval_period="hours",
        celery_task_name=CELERY_TASK, start_time=past_start,
    )
    pt.last_run_at = FIXED_NOW - timedelta(hours=7)  # last_run_at + 6h is 1h in the past
    pt.save()

    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        result = SchedulingService.compute_next_run_at(pt)

    assert result == FIXED_NOW + timedelta(hours=6)


def test_compute_next_run_at_interval_manual_trigger_advances_next_run():
    past_start = FIXED_NOW - timedelta(hours=9)  # start_time = 9h ago, interval = 6h
    pt = service.apply_schedule(
        periodic_task=None, interval=6, interval_period="hours",
        celery_task_name=CELERY_TASK, start_time=past_start,
    )
    pt.last_run_at = FIXED_NOW - timedelta(hours=1)  # manually triggered 1h ago (off-schedule)
    pt.save()

    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        result = SchedulingService.compute_next_run_at(pt)

    assert result == pt.last_run_at + timedelta(hours=6)


def test_compute_next_run_at_interval_future_start_time():
    future_start = FIXED_NOW + timedelta(hours=2)
    pt = service.apply_schedule(
        periodic_task=None,
        interval=30,
        interval_period="minutes",
        celery_task_name=CELERY_TASK,
        start_time=future_start,
    )
    with patch("django.utils.timezone.now", return_value=FIXED_NOW):
        result = SchedulingService.compute_next_run_at(pt)

    assert result == future_start
