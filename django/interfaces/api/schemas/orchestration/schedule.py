from typing import Literal
from datetime import datetime

from ninja import Field

from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
)


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


class SchedulePatchBody(BasePatchBody):
    enabled: bool = True
    start_time: datetime | None = None
    crontab: str | None = None
    interval: int | None = Field(None, ge=1)
    interval_period: Literal["minutes", "hours", "days"] | None = None
