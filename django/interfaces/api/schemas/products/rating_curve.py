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
    MonitoringSiteSummaryResponse,
)


FittingMethod = Literal["linear", "power_law"]


class RatingCurveOrderBy(OrderByField):
    id = ("id", "id")
    name = ("name", "name")
    monitoring_site_id = ("monitoringSiteId", "monitoring_site_id")
    monitoring_site_name = ("monitoringSiteName", "monitoring_site__name")
    workspace_id = ("workspaceId", "monitoring_site__workspace_id")
    workspace_name = ("workspaceName", "monitoring_site__workspace__name")


class RatingCurveQueryParameters(CollectionQueryParameters):
    order_by: list[RatingCurveOrderBy] = Query(
        [], description="Select one or more fields to order the response by."
    )
    monitoring_site: list[uuid.UUID] = Query(
        [], description="Filter rating curves by monitoring_site ID.", alias="monitoring_site_id"
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
    monitoring_site: MonitoringSiteSummaryResponse
    points: list[tuple[float, float]]

    @staticmethod
    def resolve_points(obj):
        return [(p.input_value, p.output_value) for p in obj.points.all()]


class RatingCurvePostBody(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    name: str
    description: Optional[str] = None
    fitting_method: FittingMethod
    monitoring_site_id: uuid.UUID
    points: list[tuple[float, float]] = []


class RatingCurvePatchBody(BasePatchBody):
    name: str
    description: Optional[str] = None
    fitting_method: FittingMethod
    points: list[tuple[float, float]]
