import uuid
from typing import Literal
from datetime import datetime

from ninja import Query

from core.types import ISODatetime
from interfaces.api.schemas import OrderByField, BaseGetResponse, CollectionQueryParameters


class TaskRunOrderBy(OrderByField):
    id = ("id", "id")
    status = ("status", "status")
    started_at = ("startedAt", "started_at")
    finished_at = ("finishedAt", "finished_at")


class TaskRunQueryParameters(CollectionQueryParameters):
    order_by: list[TaskRunOrderBy] = Query(
        [], description="Select one or more fields to order the response by."
    )
    status: list[Literal["PENDING", "STARTED", "SUCCESS", "FAILURE"]] = Query(
        [], description="Filters task runs by their status."
    )
    started_at__lte: ISODatetime | None = Query(
        None, description="Filters for task runs started on or before this date and time.",
        alias="started_at_max"
    )
    started_at__gte: ISODatetime | None = Query(
        None, description="Filters for task runs started on or after this date and time.",
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


class TaskRunResponse(BaseGetResponse):
    id: uuid.UUID
    status: Literal["PENDING", "STARTED", "SUCCESS", "FAILURE"]
    message: str | None = None
    result: dict | None = None
    started_at: datetime
    finished_at: datetime | None = None
