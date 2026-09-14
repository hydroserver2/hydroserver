import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

AggregationMethod = Literal["mean", "sum", "min", "max", "first", "last", "time_weighted_mean"]
Period = Literal["minutes", "hours", "days", "weeks", "months"]


class TransformationInput(BaseModel):
    datastream_id: uuid.UUID
    variable_name: Optional[str] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RatingCurveTransformation(BaseModel):
    id: uuid.UUID
    output_datastream_id: uuid.UUID
    input_datastreams: List[TransformationInput]
    rating_curve_id: uuid.UUID
    transformation_type: Literal["rating_curve"] = "rating_curve"

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @property
    def input_datastream_id(self) -> uuid.UUID:
        """The single input datastream for this rating curve transformation."""

        return self.input_datastreams[0].datastream_id


class DerivationTransformation(BaseModel):
    id: uuid.UUID
    output_datastream_id: uuid.UUID
    input_datastreams: List[TransformationInput]
    formula: str
    stop_on_no_data: bool
    stop_on_error: bool
    transformation_type: Literal["derivation"] = "derivation"

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AggregationTransformation(BaseModel):
    id: uuid.UUID
    output_datastream_id: uuid.UUID
    input_datastreams: List[TransformationInput]
    aggregation_method: AggregationMethod
    output_interval_units: Period
    output_interval: int
    timezone_type: Optional[Literal["utc", "offset", "iana"]] = None
    timezone: Optional[str] = None
    min_values: Optional[int] = None
    transformation_type: Literal["aggregation"] = "aggregation"

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @property
    def input_datastream_id(self) -> uuid.UUID:
        """The single input datastream for this aggregation transformation."""

        return self.input_datastreams[0].datastream_id
