from typing import Literal
from datetime import datetime

from ninja import Field
from pydantic import field_validator

from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
)


def resolve_schedule(obj):
    if not hasattr(obj, "periodic_task"):
        return getattr(obj, "schedule", None)

    pt = obj.periodic_task
    if not pt:
        return None

    ct = pt.crontab

    return {
        "enabled": pt.enabled,
        "start_time": pt.start_time,
        "crontab": f"{ct.minute} {ct.hour} {ct.day_of_month} {ct.month_of_year} {ct.day_of_week}" if ct else None,
        "interval": pt.interval.every if pt.interval else None,
        "interval_period": pt.interval.period if pt.interval else None,
        "next_run_at": getattr(obj, "next_run_at", None),
    }


def _validate_crontab_field_count(crontab: str | None) -> str | None:
    if crontab is not None and len(crontab.split()) != 5:
        raise ValueError("crontab must have exactly 5 space-separated fields")

    return crontab


class ScheduleResponse(BaseGetResponse):
    enabled: bool
    start_time: datetime | None = None
    crontab: str | None = None
    interval: int | None = None
    interval_period: Literal["minutes", "hours", "days"] | None = None
    next_run_at: datetime | None = None


class SchedulePostBody(BasePostBody):
    enabled: bool = True
    start_time: datetime | None = None
    crontab: str | None = None
    interval: int | None = Field(None, ge=1)
    interval_period: Literal["minutes", "hours", "days"] | None = None

    _validate_crontab = field_validator("crontab", mode="after")(_validate_crontab_field_count)


class SchedulePatchBody(BasePatchBody):
    enabled: bool = True
    start_time: datetime | None = None
    crontab: str | None = None
    interval: int | None = Field(None, ge=1)
    interval_period: Literal["minutes", "hours", "days"] | None = None

    _validate_crontab = field_validator("crontab", mode="after")(_validate_crontab_field_count)
