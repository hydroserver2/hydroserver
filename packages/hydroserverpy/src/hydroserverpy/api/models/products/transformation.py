import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

AggregationMethod = Literal["mean", "sum", "min", "max", "first", "last"]
Period = Literal["minutes", "hours", "days", "weeks", "months"]


class DatastreamSummary(BaseModel):
    id: uuid.UUID
    name: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RatingCurveSummary(BaseModel):
    id: uuid.UUID
    name: str
    fitting_method: Literal["linear", "power_law"]

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TransformationInput(BaseModel):
    datastream: DatastreamSummary
    variable_name: Optional[str] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RatingCurveTransformation(BaseModel):
    id: uuid.UUID
    output_datastream: DatastreamSummary
    input_datastream: DatastreamSummary
    rating_curve: RatingCurveSummary

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ExpressionTransformation(BaseModel):
    id: uuid.UUID
    output_datastream: DatastreamSummary
    input_datastream: DatastreamSummary
    variable_name: Optional[str] = None
    formula: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CompositeExpressionTransformation(BaseModel):
    id: uuid.UUID
    output_datastream: DatastreamSummary
    input_datastreams: List[TransformationInput]
    formula: str
    output_interval_units: Period
    output_interval: int
    max_gap_interval: Optional[int] = None
    max_gap_interval_units: Optional[Period] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AggregationTransformation(BaseModel):
    id: uuid.UUID
    output_datastream: DatastreamSummary
    input_datastream: DatastreamSummary
    aggregation_method: AggregationMethod
    output_interval_units: Period
    output_interval: int
    timezone_type: Optional[Literal["utc", "offset", "iana"]] = None
    timezone: Optional[str] = None
    min_values: Optional[int] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
