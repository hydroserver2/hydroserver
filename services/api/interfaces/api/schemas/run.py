import uuid
from typing import Literal, Optional
from datetime import datetime
from ninja import Schema, Query
from interfaces.api.types import ISODatetime
from interfaces.api.schemas import BaseGetResponse, BasePostBody, BasePatchBody, CollectionQueryParameters


_order_by_fields = (
    "status", "startedAt", "finishedAt"
)

TaskRunOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]


class TaskRunQueryParameters(CollectionQueryParameters):
    order_by: list[TaskRunOrderByFields] | None = Query(
        [], description="Select one or more fields to order the response by."
    )
    status: list[str | Literal["null"]] = Query(
        [], description="Filters task runs by their status."
    )
    started_at__lte: ISODatetime | None = Query(
        None, description="Filters for task runs created on or before this date and time.",
        alias="started_at_max"
    )
    started_at__gte: ISODatetime | None = Query(
        None, description="Filters for task runs created on or after this date and time.",
        alias="started_at_min"
    )
    finished_at__lte: ISODatetime | None = Query(
        None, description="Filters for task runs finished on or before this date and time.",
        alias="finished_at_max"
    )
    finished_at__gte: ISODatetime | None = Query(
        None, description="Filters for task runs finished on or after this date and time.",
        alias="finished_at_min"
    )


class TaskRunFields(Schema):
    status: Literal["RUNNING", "SUCCESS", "FAILURE"]
    result: dict | None = None
    started_at: datetime
    finished_at: datetime | None = None


class TaskRunResponse(BaseGetResponse, TaskRunFields):
    id: uuid.UUID


class TaskRunPostBody(BasePostBody, TaskRunFields):
    id: Optional[uuid.UUID] = None


class TaskRunPatchBody(BasePatchBody, TaskRunFields):
    pass
