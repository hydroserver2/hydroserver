import json
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional, Literal, Union
from pydantic import validate_call, ConfigDict
from croniter import croniter

from django.utils import timezone
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

from core.types import Unset


class SchedulingService:

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def apply_schedule(
        self,
        periodic_task: Optional[PeriodicTask],
        crontab: Union[Optional[str], Unset] = Unset,
        interval: Union[Optional[int], Unset] = Unset,
        interval_period: Union[Optional[Literal["minutes", "hours", "days"]], Unset] = Unset,
        start_time: Union[Optional[datetime], Unset] = Unset,
        enabled: Union[bool, Unset] = Unset,
        celery_task_name: Union[Optional[str], Unset] = Unset,
        celery_task_kwargs: Union[Optional[dict], Unset] = Unset,
        periodic_task_name: Union[Optional[str], Unset] = Unset,
    ) -> Union[PeriodicTask, None]:
        """
        Update or create a PeriodicTask with a crontab or interval schedule.
        """

        now = timezone.now()

        if crontab not in (None, Unset) and interval not in (None, Unset):
            raise ValueError("Only one of crontab or interval can be set on a schedule.")

        current_crontab = (
            self.get_crontab_string(periodic_task)
            if periodic_task else None
        )
        current_interval = (
            periodic_task.interval.every  # noqa
            if periodic_task and periodic_task.interval else None
        )
        current_interval_period = (
            periodic_task.interval.period  # noqa
            if periodic_task and periodic_task.interval else None
        )

        crontab_schedule = None
        interval_schedule = None

        if crontab not in (None, Unset):
            try:
                croniter(crontab, datetime.now())
                minute, hour, day, month, weekday = crontab.strip().split()
            except (ValueError, AttributeError):
                raise ValueError(f"Invalid crontab schedule {crontab}.")

            if current_crontab:
                if crontab != current_crontab:
                    pt_crontab: CrontabSchedule = periodic_task.crontab
                    pt_crontab.minute = minute
                    pt_crontab.hour = hour
                    pt_crontab.day_of_month = day
                    pt_crontab.month_of_year = month
                    pt_crontab.day_of_week = weekday
                    pt_crontab.save()
                    crontab_schedule = pt_crontab
                else:
                    crontab_schedule = periodic_task.crontab

            else:
                if current_interval:
                    old_interval_schedule = periodic_task.interval
                    PeriodicTask.objects.filter(pk=periodic_task.pk).update(interval=None)
                    old_interval_schedule.delete()

                crontab_schedule = CrontabSchedule.objects.create(
                    minute=minute,
                    hour=hour,
                    day_of_month=day,
                    month_of_year=month,
                    day_of_week=weekday,
                )

        if interval not in (None, Unset):
            if interval < 1:
                raise ValueError("Schedule interval must be at least 1.")

            if interval_period is Unset:
                raise ValueError("interval_period is required when setting an interval schedule.")

            if current_interval:
                if interval != current_interval or current_interval_period != interval_period:
                    pt_interval: IntervalSchedule = periodic_task.interval
                    pt_interval.every = interval
                    if interval_period is not Unset:
                        pt_interval.period = interval_period
                    pt_interval.save()
                    interval_schedule = pt_interval
                else:
                    interval_schedule = periodic_task.interval

            else:
                if current_crontab:
                    old_crontab = periodic_task.crontab
                    PeriodicTask.objects.filter(pk=periodic_task.pk).update(crontab=None)
                    old_crontab.delete()

                interval_schedule = IntervalSchedule.objects.create(
                    every=interval,
                    period=interval_period if interval_period is not Unset else None,
                )

        if periodic_task:
            if (crontab is not Unset or interval is not Unset) and not crontab_schedule and not interval_schedule:
                self.delete_schedule(periodic_task)
                periodic_task = None

            elif crontab is not Unset or interval is not Unset:
                periodic_task.crontab = crontab_schedule
                periodic_task.interval = interval_schedule
                periodic_task.date_changed = now

            if periodic_task is not None:
                periodic_task.enabled = enabled if enabled is not Unset else periodic_task.enabled

                if start_time is not Unset:
                    new_start_time = start_time or now
                    periodic_task.start_time = new_start_time
                    if periodic_task.interval:
                        delta = periodic_task.schedule.run_every
                        if new_start_time <= now:
                            n = int((now - new_start_time).total_seconds() / delta.total_seconds())
                            periodic_task.last_run_at = new_start_time + n * delta
                        else:
                            periodic_task.last_run_at = None

                if periodic_task_name not in (None, Unset):
                    periodic_task.name = periodic_task_name

                periodic_task.save()

            return periodic_task

        else:
            if not crontab_schedule and not interval_schedule:
                periodic_task = None

            else:
                if not celery_task_name:
                    raise ValueError("celery_task_name is required when creating a new schedule.")

                effective_start = (
                    start_time if start_time not in (None, Unset) else now
                )

                if interval_schedule and effective_start <= now:
                    delta = interval_schedule.schedule.run_every
                    n = int((now - effective_start).total_seconds() / delta.total_seconds())
                    initial_last_run_at = effective_start + n * delta
                elif crontab_schedule and effective_start <= now:
                    initial_last_run_at = now
                else:
                    initial_last_run_at = None

                periodic_task = PeriodicTask.objects.create(
                    name=periodic_task_name if periodic_task_name not in (None, Unset) else "",
                    task=celery_task_name,
                    kwargs=json.dumps(celery_task_kwargs if celery_task_kwargs not in (None, Unset) else {}),
                    enabled=enabled if enabled is not Unset else True,
                    date_changed=now,
                    crontab=crontab_schedule,
                    interval=interval_schedule,
                    start_time=effective_start,
                    last_run_at=initial_last_run_at,
                    expire_seconds=3600,
                )

            return periodic_task

    @staticmethod
    def delete_schedule(periodic_task: PeriodicTask) -> None:
        """
        Delete a PeriodicTask and its associated crontab or interval schedule.
        """

        if periodic_task.crontab_id:
            old_crontab = periodic_task.crontab
            PeriodicTask.objects.filter(pk=periodic_task.pk).update(crontab=None)
            old_crontab.delete()

        if periodic_task.interval_id:
            old_interval = periodic_task.interval
            PeriodicTask.objects.filter(pk=periodic_task.pk).update(interval=None)
            old_interval.delete()

        periodic_task.delete()

    @staticmethod
    def get_crontab_string(periodic_task: PeriodicTask) -> Optional[str]:
        """
        Return the crontab schedule of a PeriodicTask as a cron expression string, or None.
        """

        if not periodic_task.crontab:
            return None

        ct = periodic_task.crontab

        return f"{ct.minute} {ct.hour} {ct.day_of_month} {ct.month_of_year} {ct.day_of_week}"

    @staticmethod
    def compute_next_run_at(periodic_task: Optional[PeriodicTask]) -> Optional[datetime]:
        """
        Return the next scheduled run time for a PeriodicTask, or None if unscheduled/disabled.
        """

        if not periodic_task or not periodic_task.enabled:
            return None

        now = timezone.now()

        if periodic_task.crontab:
            cron_string = SchedulingService.get_crontab_string(periodic_task)
            base = periodic_task.start_time if periodic_task.start_time and periodic_task.start_time > now else now
            base_naive = timezone.make_naive(base, dt_timezone.utc)
            next_dt = croniter(cron_string, base_naive).get_next(datetime)
            return timezone.make_aware(next_dt, dt_timezone.utc)

        if periodic_task.interval:
            period_deltas = {
                "days": timedelta(days=periodic_task.interval.every),
                "hours": timedelta(hours=periodic_task.interval.every),
                "minutes": timedelta(minutes=periodic_task.interval.every),
            }
            delta = period_deltas.get(periodic_task.interval.period)
            if not delta:
                return None
            if periodic_task.start_time and periodic_task.start_time > now:
                return periodic_task.start_time
            if periodic_task.last_run_at:
                next_run = periodic_task.last_run_at + delta
                if next_run > now:
                    return next_run
            return now + delta

        return None
