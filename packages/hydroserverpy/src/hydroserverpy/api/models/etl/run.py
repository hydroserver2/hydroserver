import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TaskRun(BaseModel):
    id: uuid.UUID
    status: str
    result: Optional[dict] = None
    started_at: Optional[datetime] = Field(None, alias="startedAt")
    finished_at: Optional[datetime] = Field(None, alias="finishedAt")

    class Config:
        populate_by_name = True
