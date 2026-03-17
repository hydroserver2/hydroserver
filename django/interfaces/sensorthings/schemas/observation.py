from uuid import UUID
from ninja import Schema, Field
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional, Union
from sensorthings.types import ISOTimeString, ISOIntervalString
from sensorthings.components.observations.schemas import (
    ObservationPostBody as DefaultObservationPostBody,
)
from sensorthings.extensions.dataarray.schemas import (
    ObservationGetResponse as DefaultObservationGetResponse,
    ObservationListResponse as DefaultObservationListResponse,
    ObservationDataArrayResponse as DefaultObservationDataArrayResponse,
    ObservationDataArrayPostBody as DefaultObservationDataArrayPostBody,
)


class ObservationResultQualityResponse(Schema):
    quality_code: Optional[str] = Field(None, alias="qualityCode")
    result_qualifiers: list[str] = Field(None, alias="resultQualifiers")

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


class ObservationResultQualityBody(Schema):
    quality_code: Optional[str] = None
    result_qualifiers: Optional[list[str]] = None

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


dataArrayList = list[
    list[
        Union[
            UUID,
            float,
            ISOTimeString,
            ISOIntervalString,
            ObservationResultQualityResponse,
            dict,
        ]
    ]
]
dataArrayPost = list[
    list[
        Union[
            UUID,
            float,
            ISOTimeString,
            ISOIntervalString,
            ObservationResultQualityBody,
            dict,
        ]
    ]
]


class ObservationDataArrayResponse(DefaultObservationDataArrayResponse):
    data_array: dataArrayList

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


class ObservationGetResponse(DefaultObservationGetResponse):
    result_quality: ObservationResultQualityResponse = None

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


class ObservationListResponse(DefaultObservationListResponse):
    value: Union[list[ObservationGetResponse], list[ObservationDataArrayResponse]]


class ObservationPostBody(DefaultObservationPostBody):
    result_quality: ObservationResultQualityBody = None

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


class ObservationDataArrayPostBody(DefaultObservationDataArrayPostBody):
    data_array: dataArrayPost

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )
