import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

AggregationMethod = Literal["mean", "sum", "min", "max", "first", "last", "time_weighted_mean"]
Period = Literal["minutes", "hours", "days", "weeks", "months"]


class RatingCurveTransformation(BaseModel):
    id: uuid.UUID
    output_datastream_id: uuid.UUID
    input_datastream_id: uuid.UUID
    rating_curve_id: uuid.UUID

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DerivationTransformation(BaseModel):
    id: uuid.UUID
    output_datastream_id: uuid.UUID
    input_datastream_ids: List[uuid.UUID]
    formula: str
    stop_on_no_data: bool
    stop_on_error: bool

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AggregationTransformation(BaseModel):
    id: uuid.UUID
    output_datastream_id: uuid.UUID
    input_datastream_id: uuid.UUID
    aggregation_method: AggregationMethod
    output_interval_units: Period
    output_interval: int
    timezone_type: Optional[Literal["utc", "offset", "iana"]] = None
    timezone: Optional[str] = None
    min_values: Optional[int] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
