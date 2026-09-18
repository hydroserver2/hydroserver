import uuid

from typing import Optional, Literal, Annotated
from pydantic import BeforeValidator, WithJsonSchema
from pydantic.alias_generators import to_camel
from ninja import Schema, Field, Query

from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    MonitoringSiteResponse,
    split_comma_separated,
    comma_array_schema,
)


FittingMethod = Literal["linear", "power_law"]


class RatingCurveFields(Schema):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    fitting_method: FittingMethod
    points: list[tuple[float, float]] = []


RATING_CURVE_INCLUDE_RELATIONS = {
    "monitoringSite": {
        "path": "monitoring_site",
        "bucket": "monitoringSites",
        "response_schema": MonitoringSiteResponse,
    },
}
RatingCurveIncludeRelation = Literal[*RATING_CURVE_INCLUDE_RELATIONS.keys()]

_sortby_fields = (
    "id",
    "name",
    "monitoringSiteId",
    "monitoringSiteName",
    "workspaceId",
    "workspaceName",
    "fittingMethod",
)
RatingCurveSortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]

_property_fields = (
    "id",
    "monitoringSiteId",
    *(to_camel(name) for name in RatingCurveFields.model_fields),
)
RatingCurvePropertyName = Literal[*_property_fields]


class RatingCurveFilterFields(Schema):
    properties: Annotated[
        Optional[list[RatingCurvePropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(RatingCurvePropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[RatingCurveIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(RatingCurveIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class RatingCurveItemQueryParameters(RatingCurveFilterFields, BaseQueryParameters):
    pass


class RatingCurveQueryParameters(RatingCurveFilterFields, CollectionQueryParameters):
    sortby: Optional[list[RatingCurveSortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )
    q: Optional[str] = Query(
        None,
        description="Full-text search query. Comma-separated terms are combined with OR; "
        "whitespace-separated words within a term are combined with AND.",
    )
    monitoring_site_id: list[uuid.UUID] = Query(
        [], description="Filter rating curves by monitoring site ID."
    )
    monitoring_site__workspace_id: list[uuid.UUID] = Query(
        [], description="Filter rating curves by workspace ID.", alias="workspace_id"
    )


class RatingCurveResponse(BaseGetResponse, RatingCurveFields):
    id: uuid.UUID
    monitoring_site_id: uuid.UUID

    @staticmethod
    def resolve_points(obj):
        points = getattr(obj, "points", None)
        if not hasattr(points, "all"):
            return points

        return [(p.input_value, p.output_value) for p in points.all()]


class RatingCurvePostBody(BasePostBody, RatingCurveFields):
    id: Optional[uuid.UUID] = None
    monitoring_site_id: uuid.UUID


class RatingCurvePatchBody(BasePatchBody, RatingCurveFields):
    pass
