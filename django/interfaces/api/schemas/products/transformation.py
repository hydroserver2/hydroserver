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
    DatastreamSummaryResponse,
)
from interfaces.api.schemas.products.rating_curve import RatingCurveSummaryResponse


AggregationMethod = Literal["mean", "sum", "min", "max", "first", "last"]
Period = Literal["minutes", "hours", "days", "weeks", "months"]
TimezoneType = Literal["utc", "offset", "iana"]


class DataProductTransformationOrderBy(OrderByField):
    id = ("id", "id")
    output_datastream_id = ("outputDatastreamId", "output_datastream_id")


class DataProductTransformationTypeQueryParameters(CollectionQueryParameters):
    order_by: list[DataProductTransformationOrderBy] = Query(
        [], description="Select one or more fields to order the response by."
    )
    output_datastream: list[uuid.UUID] = Query(
        [], description="Filter by output datastream ID.", alias="output_datastream_id"
    )
    input_datastream: list[uuid.UUID] = Query(
        [], description="Filter by input datastream ID.", alias="input_datastream_id"
    )


# --- Composite expression input schemas ---

class TransformationInputResponse(BaseGetResponse):
    datastream: DatastreamSummaryResponse
    variable_name: Optional[str] = None


class TransformationInputPostBody(BasePostBody):
    datastream: uuid.UUID = Field(alias="datastreamId")
    variable_name: str


# --- Per-type response schemas ---

class RatingCurveTransformationResponse(BaseGetResponse):
    id: uuid.UUID
    output_datastream: DatastreamSummaryResponse
    input_datastream: DatastreamSummaryResponse
    rating_curve: RatingCurveSummaryResponse

    @staticmethod
    def resolve_input_datastream(obj):
        first = obj.input_datastreams.first()
        return first.datastream if first else None


class ExpressionTransformationResponse(BaseGetResponse):
    id: uuid.UUID
    output_datastream: DatastreamSummaryResponse
    input_datastream: DatastreamSummaryResponse
    variable_name: Optional[str] = None
    formula: str

    @staticmethod
    def resolve_input_datastream(obj):
        first = obj.input_datastreams.first()
        return first.datastream if first else None

    @staticmethod
    def resolve_variable_name(obj):
        first = obj.input_datastreams.first()
        return first.variable_name if first else None


class CompositeExpressionTransformationResponse(BaseGetResponse):
    id: uuid.UUID
    output_datastream: DatastreamSummaryResponse
    input_datastreams: list[TransformationInputResponse]
    formula: str
    output_interval_units: Period
    output_interval: int
    max_gap_interval: Optional[int] = None
    max_gap_interval_units: Optional[Period] = None

    @staticmethod
    def resolve_input_datastreams(obj):
        return obj.input_datastreams.all()


class AggregationTransformationResponse(BaseGetResponse):
    id: uuid.UUID
    output_datastream: DatastreamSummaryResponse
    input_datastream: DatastreamSummaryResponse
    aggregation_method: AggregationMethod
    output_interval_units: Period
    output_interval: int
    timezone_type: Optional[TimezoneType] = None
    timezone: Optional[str] = None
    min_values: Optional[int] = None

    @staticmethod
    def resolve_input_datastream(obj):
        first = obj.input_datastreams.first()
        return first.datastream if first else None


# --- Per-type post body schemas ---

class _TransformationPostBodyBase(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    output_datastream: uuid.UUID = Field(alias="outputDatastreamId")


class RatingCurveTransformationPostBody(_TransformationPostBodyBase):
    input_datastream: uuid.UUID = Field(alias="inputDatastreamId")
    rating_curve: uuid.UUID = Field(alias="ratingCurveId")


class ExpressionTransformationPostBody(_TransformationPostBodyBase):
    input_datastream: uuid.UUID = Field(alias="inputDatastreamId")
    variable_name: str
    formula: str


class CompositeExpressionTransformationPostBody(_TransformationPostBodyBase):
    input_datastreams: list[TransformationInputPostBody]
    formula: str
    output_interval_units: Period
    output_interval: int
    max_gap_interval: Optional[int] = None
    max_gap_interval_units: Optional[Period] = None


class AggregationTransformationPostBody(_TransformationPostBodyBase):
    input_datastream: uuid.UUID = Field(alias="inputDatastreamId")
    aggregation_method: AggregationMethod
    output_interval_units: Period
    output_interval: int
    timezone_type: Optional[TimezoneType] = None
    timezone: Optional[str] = None
    min_values: Optional[int] = None


# --- Per-type patch body schemas ---

class RatingCurveTransformationPatchBody(BasePatchBody):
    output_datastream: uuid.UUID = Field(alias="outputDatastreamId")
    input_datastream: uuid.UUID = Field(alias="inputDatastreamId")
    rating_curve: uuid.UUID = Field(alias="ratingCurveId")


class ExpressionTransformationPatchBody(BasePatchBody):
    output_datastream: uuid.UUID = Field(alias="outputDatastreamId")
    input_datastream: uuid.UUID = Field(alias="inputDatastreamId")
    variable_name: Optional[str]
    formula: str


class CompositeExpressionTransformationPatchBody(BasePatchBody):
    output_datastream: uuid.UUID = Field(alias="outputDatastreamId")
    input_datastreams: list[TransformationInputPostBody]
    formula: str
    output_interval_units: Period
    output_interval: int
    max_gap_interval: Optional[int]
    max_gap_interval_units: Optional[Period]


class AggregationTransformationPatchBody(BasePatchBody):
    output_datastream: uuid.UUID = Field(alias="outputDatastreamId")
    input_datastream: uuid.UUID = Field(alias="inputDatastreamId")
    aggregation_method: AggregationMethod
    output_interval_units: Period
    output_interval: int
    timezone_type: Optional[TimezoneType]
    timezone: Optional[str]
    min_values: Optional[int]
