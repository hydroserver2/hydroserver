import uuid

from typing import Optional, Literal, Annotated
from pydantic import BeforeValidator, WithJsonSchema
from pydantic.alias_generators import to_camel
from ninja import Schema, Query

from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    DatastreamResponse,
    split_comma_separated,
    comma_array_schema,
)
from interfaces.api.schemas.products.rating_curve import RatingCurveResponse


TransformationType = Literal["rating_curve", "derivation", "aggregation"]
AggregationMethod = Literal["mean", "sum", "min", "max", "first", "last", "time_weighted_mean"]
Period = Literal["minutes", "hours", "days", "weeks", "months"]
TimezoneType = Literal["offset", "iana"]


class TransformationInputResponse(BaseGetResponse):
    datastream_id: uuid.UUID
    variable_name: Optional[str] = None


class TransformationInputPostBody(BasePostBody):
    datastream_id: uuid.UUID
    variable_name: Optional[str] = None


class DataProductTransformationFields(Schema):
    output_datastream_id: uuid.UUID
    input_datastreams: list[TransformationInputPostBody] = []
    rating_curve_id: Optional[uuid.UUID] = None
    formula: Optional[str] = None
    aggregation_method: Optional[AggregationMethod] = None
    output_interval_units: Optional[Period] = None
    output_interval: Optional[int] = None
    timezone_type: Optional[TimezoneType] = None
    timezone: Optional[str] = None
    min_values: Optional[int] = None
    stop_on_no_data: bool = True
    stop_on_error: bool = True


DATA_PRODUCT_TRANSFORMATION_INCLUDE_RELATIONS = {
    "outputDatastream": {
        "path": "output_datastream",
        "bucket": "outputDatastreams",
        "response_schema": DatastreamResponse,
    },
    "ratingCurve": {
        "path": "rating_curve",
        "bucket": "ratingCurves",
        "response_schema": RatingCurveResponse,
    },
}
DataProductTransformationIncludeRelation = Literal[
    *DATA_PRODUCT_TRANSFORMATION_INCLUDE_RELATIONS.keys()
]

_sortby_fields = ("id", "outputDatastreamId", "transformationType")
DataProductTransformationSortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]

_property_fields = (
    "id",
    "transformationType",
    *(to_camel(name) for name in DataProductTransformationFields.model_fields),
)
DataProductTransformationPropertyName = Literal[*_property_fields]


class DataProductTransformationFilterFields(Schema):
    properties: Annotated[
        Optional[list[DataProductTransformationPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(DataProductTransformationPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[DataProductTransformationIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(DataProductTransformationIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class DataProductTransformationItemQueryParameters(
    DataProductTransformationFilterFields, BaseQueryParameters
):
    pass


class DataProductTransformationQueryParameters(
    DataProductTransformationFilterFields, CollectionQueryParameters
):
    sortby: Optional[list[DataProductTransformationSortByFields]] = Query(
        [], description="Select one or more fields to sort the response by."
    )
    transformation_type: list[str] = Query(
        [], description="Filter transformations by type."
    )
    output_datastream_id: list[uuid.UUID] = Query(
        [], description="Filter transformations by output datastream ID."
    )
    input_datastreams__datastream_id: list[uuid.UUID] = Query(
        [], description="Filter transformations by input datastream ID.", alias="input_datastream_id"
    )


class DataProductTransformationResponse(BaseGetResponse, DataProductTransformationFields):
    id: uuid.UUID
    transformation_type: TransformationType
    input_datastreams: list[TransformationInputResponse] = []


class DataProductTransformationPostBody(BasePostBody, DataProductTransformationFields):
    id: Optional[uuid.UUID] = None
    transformation_type: TransformationType


class DataProductTransformationPatchBody(BasePatchBody, DataProductTransformationFields):
    pass
