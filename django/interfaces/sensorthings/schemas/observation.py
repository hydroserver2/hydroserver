from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional


class ObservationResultQuality(BaseModel):
    quality_code: Optional[str] = None
    result_qualifiers: Optional[list[str]] = None

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


class ObservationProperties(BaseModel):
    result_quality: Optional[ObservationResultQuality] = None

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )
