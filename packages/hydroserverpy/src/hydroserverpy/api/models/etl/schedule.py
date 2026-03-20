from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class TaskSchedule(BaseModel):
    start_time: Optional[datetime] = Field(None, alias="startTime")
    next_run_at: Optional[datetime] = Field(None, alias="nextRunAt")
    paused: bool = False
    interval: Optional[int] = Field(None, gt=0)
    interval_period: Optional[Literal["minutes", "hours", "days"]] = Field(
        None, alias="intervalPeriod"
    )
    crontab: Optional[str]

    class Config:
        populate_by_name = True
