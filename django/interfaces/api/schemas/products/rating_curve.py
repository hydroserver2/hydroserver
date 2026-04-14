import uuid
from typing import Optional, Literal

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


FittingMethod = Literal["linear", "power_law", "polynomial"]


class RatingCurveOrderBy(OrderByField):
    id = ("id", "id")
    name = ("name", "name")
    thing_id = ("thingId", "thing_id")
    thing_name = ("thingName", "thing__name")
    workspace_id = ("workspaceId", "thing__workspace_id")
    workspace_name = ("workspaceName", "thing__workspace__name")


class RatingCurveQueryParameters(CollectionQueryParameters):
    order_by: list[RatingCurveOrderBy] = Query(
        [], description="Select one or more fields to order the response by."
    )
    thing: list[uuid.UUID] = Query(
        [], description="Filter rating curves by thing ID.", alias="thing_id"
    )
    workspace: list[uuid.UUID] = Query(
        [], description="Filter rating curves by workspace ID.", alias="workspace_id"
    )


class RatingCurveSummaryResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    fitting_method: FittingMethod


class RatingCurveResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    fitting_method: FittingMethod
    thing: ThingSummaryResponse
    points: list[tuple[float, float]]

    @staticmethod
    def resolve_points(obj):
        return [(p.input_value, p.output_value) for p in obj.points.all()]


class RatingCurvePostBody(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    name: str
    description: Optional[str] = None
    fitting_method: FittingMethod
    thing_id: uuid.UUID
    points: list[tuple[float, float]] = []


class RatingCurvePatchBody(BasePatchBody):
    name: str
    description: Optional[str] = None
    fitting_method: FittingMethod
    points: list[tuple[float, float]]
