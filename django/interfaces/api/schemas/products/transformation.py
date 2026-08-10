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


AggregationMethod = Literal["mean", "sum", "min", "max", "first", "last", "time_weighted_mean"]
Period = Literal["minutes", "hours", "days", "weeks", "months"]
TimezoneType = Literal["offset", "iana"]


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


# --- Derivation input schemas ---

class TransformationInputResponse(BaseGetResponse):
    datastream: DatastreamSummaryResponse
    variable_name: Optional[str] = None


class TransformationInputPostBody(BasePostBody):
    datastream: uuid.UUID = Field(alias="datastreamId")
    variable_name: str


# --- Per-type summary response schemas (IDs only for datastreams) ---

class RatingCurveTransformationSummaryResponse(BaseGetResponse):
    id: uuid.UUID
    output_datastream_id: uuid.UUID
    input_datastream_id: uuid.UUID
    rating_curve_id: uuid.UUID

    @staticmethod
    def resolve_input_datastream_id(obj):
        if not hasattr(obj, "input_datastreams"):
            return getattr(obj, "input_datastream_id", None)
        first = next(iter(obj.input_datastreams.all()), None)
        return first.datastream_id if first else None


class DerivationTransformationSummaryResponse(BaseGetResponse):
    id: uuid.UUID
    output_datastream_id: uuid.UUID
    input_datastream_ids: list[uuid.UUID]
    formula: str
    stop_on_no_data: bool
    stop_on_error: bool

    @staticmethod
    def resolve_input_datastream_ids(obj):
        if not hasattr(obj, "input_datastreams"):
            return getattr(obj, "input_datastream_ids", [])
        return [i.datastream_id for i in obj.input_datastreams.all()]


class AggregationTransformationSummaryResponse(BaseGetResponse):
    id: uuid.UUID
    output_datastream_id: uuid.UUID
    input_datastream_id: uuid.UUID
    aggregation_method: AggregationMethod
    output_interval_units: Period
    output_interval: int
    timezone_type: Optional[TimezoneType] = None
    timezone: Optional[str] = None
    min_values: Optional[int] = None

    @staticmethod
    def resolve_input_datastream_id(obj):
        if not hasattr(obj, "input_datastreams"):
            return getattr(obj, "input_datastream_id", None)
        first = next(iter(obj.input_datastreams.all()), None)
        return first.datastream_id if first else None


# --- Per-type detail response schemas ---

class RatingCurveTransformationResponse(BaseGetResponse):
    id: uuid.UUID
    output_datastream: DatastreamSummaryResponse
    input_datastream: DatastreamSummaryResponse
    rating_curve: RatingCurveSummaryResponse

    @staticmethod
    def resolve_input_datastream(obj):
        if not hasattr(obj, "input_datastreams"):
            return getattr(obj, "input_datastream", None)
        first = next(iter(obj.input_datastreams.all()), None)
        return first.datastream if first else None


class DerivationTransformationResponse(BaseGetResponse):
    id: uuid.UUID
    output_datastream: DatastreamSummaryResponse
    input_datastreams: list[TransformationInputResponse]
    formula: str
    stop_on_no_data: bool
    stop_on_error: bool

    @staticmethod
    def resolve_input_datastreams(obj):
        if not hasattr(obj.input_datastreams, "all"):
            return obj.input_datastreams
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
        if not hasattr(obj, "input_datastreams"):
            return getattr(obj, "input_datastream", None)
        first = next(iter(obj.input_datastreams.all()), None)
        return first.datastream if first else None


# --- Per-type post body schemas ---

class _TransformationPostBodyBase(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    output_datastream: uuid.UUID = Field(alias="outputDatastreamId")


class RatingCurveTransformationPostBody(_TransformationPostBodyBase):
    input_datastream: uuid.UUID = Field(alias="inputDatastreamId")
    rating_curve: uuid.UUID = Field(alias="ratingCurveId")


class DerivationTransformationPostBody(_TransformationPostBodyBase):
    input_datastreams: list[TransformationInputPostBody]
    formula: str
    stop_on_no_data: bool = True
    stop_on_error: bool = True


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


class DerivationTransformationPatchBody(BasePatchBody):
    output_datastream: uuid.UUID = Field(alias="outputDatastreamId")
    input_datastreams: list[TransformationInputPostBody]
    formula: str
    stop_on_no_data: bool
    stop_on_error: bool


class AggregationTransformationPatchBody(BasePatchBody):
    output_datastream: uuid.UUID = Field(alias="outputDatastreamId")
    input_datastream: uuid.UUID = Field(alias="inputDatastreamId")
    aggregation_method: AggregationMethod
    output_interval_units: Period
    output_interval: int
    timezone_type: Optional[TimezoneType] = None
    timezone: Optional[str] = None
    min_values: Optional[int] = None
