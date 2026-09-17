import uuid

from datetime import datetime
from typing import Literal, Optional, Annotated
from ninja import Query
from pydantic import BeforeValidator, WithJsonSchema

from core.types import ISODatetime
from interfaces.api.schemas import (
    BaseGetResponse,
    CollectionQueryParameters,
    split_comma_separated,
    comma_array_schema,
)


_sortby_fields = ("id", "status", "startedAt", "finishedAt")
TaskRunSortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]

TaskRunPropertyName = Literal[
    "id", "status", "message", "result", "startedAt", "finishedAt"
]


class TaskRunQueryParameters(CollectionQueryParameters):
    properties: Annotated[
        Optional[list[TaskRunPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(TaskRunPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    sortby: list[TaskRunSortByFields] = Query(
        [], description="Select one or more fields to sort the response by."
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


def resolve_latest_run(obj):
    if not hasattr(obj, "latest_run_id"):
        return getattr(obj, "latest_run", None)
    if not getattr(obj, "latest_run_id", None):
        return None

    return {
        "id": obj.latest_run_id,
        "status": obj.latest_run_status,
        "started_at": obj.latest_run_started_at,
        "finished_at": obj.latest_run_finished_at,
        "message": obj.latest_run_message,
        "result": obj.latest_run_result,
    }
