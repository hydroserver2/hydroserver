import uuid
from typing import Optional

from ninja import Field, Query

from core.types import Unset
from interfaces.api.schemas import (
    OrderByField,
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
    ThingSummaryResponse,
)


class ExpressionOrderBy(OrderByField):
    id = ("id", "id")
    name = ("name", "name")
    thing_id = ("thingId", "thing_id")
    thing_name = ("thingName", "thing__name")
    workspace_id = ("workspaceId", "thing__workspace_id")
    workspace_name = ("workspaceName", "thing__workspace__name")


class ExpressionQueryParameters(CollectionQueryParameters):
    order_by: list[ExpressionOrderBy] = Query(
        [], description="Select one or more fields to order the response by."
    )
    thing: list[uuid.UUID] = Query(
        [], description="Filter expressions by thing ID.", alias="thing_id"
    )
    workspace: list[uuid.UUID] = Query(
        [], description="Filter expressions by workspace ID.", alias="workspace_id"
    )


class ExpressionSegmentResponse(BaseGetResponse):
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    formula: Optional[str] = None


class ExpressionResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    breakpoint_variable: Optional[str] = None
    thing: ThingSummaryResponse
    segments: list[ExpressionSegmentResponse]

    @staticmethod
    def resolve_segments(obj):
        return obj.segments.all()


class ExpressionSegmentPostBody(BasePostBody):
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    formula: Optional[str] = None


class ExpressionPostBody(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    name: str
    description: Optional[str] = None
    thing_id: uuid.UUID
    breakpoint_variable: Optional[str] = None
    segments: list[ExpressionSegmentPostBody] = []


class ExpressionPatchBody(BasePatchBody):
    name: str
    description: Optional[str] = None
    breakpoint_variable: Optional[str] = None
    segments: list[ExpressionSegmentPostBody] = []
