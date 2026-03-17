from ninja import Schema, Field
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel
from typing import Literal, Optional
from sensorthings.types import AnyHttpUrlString
from sensorthings.components.sensors.schemas import (
    SensorGetResponse as DefaultSensorGetResponse,
    SensorListResponse as DefaultSensorListResponse,
)
from .workspace import WorkspaceProperties


class SensorModel(Schema):
    sensor_model_name: Optional[str] = None
    sensor_model_url: Optional[AnyHttpUrlString] = None
    sensor_manufacturer: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


KnownSensorEncodingTypes = Literal[
    "application/pdf",
    "http://www.opengis.net/doc/IS/SensorML/2.0",
    "text/html",
    "text/plain",
    "application/json",
    "text/plain",
]

# Legacy deployments may contain other valid MIME strings in this field.
# Keep known values documented while accepting arbitrary encodings to avoid
# response-validation 500s when reading existing records.
sensorEncodingTypes = KnownSensorEncodingTypes | str


class SensorMetadata(Schema):
    method_code: Optional[str] = None
    method_type: str
    method_link: Optional[AnyHttpUrlString] = None
    sensor_model: SensorModel

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


class SensorProperties(Schema):
    workspace: Optional[WorkspaceProperties] = None


class SensorGetResponse(DefaultSensorGetResponse):
    encoding_type: sensorEncodingTypes
    sensor_metadata: SensorMetadata = Field(..., alias="metadata")
    properties: SensorProperties

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


class SensorListResponse(DefaultSensorListResponse):
    value: list[SensorGetResponse]
