import uuid
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class TaskRun(BaseModel):
    id: uuid.UUID
    status: Literal["PENDING", "STARTED", "SUCCESS", "FAILURE"]
    message: Optional[str] = None
    result: Optional[dict] = None
    started_at: Optional[datetime] = Field(None, alias="startedAt")
    finished_at: Optional[datetime] = Field(None, alias="finishedAt")

    class Config:
        populate_by_name = True
