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


FittingMethod = Literal["linear", "power_law", "polynomial", "spline"]


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


class RatingCurveSegmentResponse(BaseGetResponse):
    fitting_method: FittingMethod
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None


class RatingCurvePointResponse(BaseGetResponse):
    input_value: float
    output_value: Optional[float] = None


class RatingCurveResponse(BaseGetResponse):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    thing: ThingSummaryResponse
    segments: list[RatingCurveSegmentResponse]
    points: list[RatingCurvePointResponse]

    @staticmethod
    def resolve_segments(obj):
        return obj.segments.all()

    @staticmethod
    def resolve_points(obj):
        return obj.points.all()


class RatingCurveSegmentPostBody(BasePostBody):
    fitting_method: FittingMethod
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None


class RatingCurvePointPostBody(BasePostBody):
    input_value: float
    output_value: Optional[float] = None


class RatingCurvePostBody(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    name: str
    description: Optional[str] = None
    thing_id: uuid.UUID
    segments: list[RatingCurveSegmentPostBody] = []
    points: list[RatingCurvePointPostBody] = []


class RatingCurvePatchBody(BasePatchBody):
    name: str
    description: Optional[str] = None
    segments: list[RatingCurveSegmentPostBody] = []
    points: list[RatingCurvePointPostBody] = []
