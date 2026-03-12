from ninja import Schema, Query
from typing import Optional, Any
from pydantic import AliasGenerator, AliasChoices, ConfigDict, field_validator
from pydantic.alias_generators import to_camel
from sensorthings.validators import PartialSchema


base_alias_generator = AliasGenerator(
    serialization_alias=lambda field_name: to_camel(field_name),
    validation_alias=lambda field_name: AliasChoices(to_camel(field_name), field_name),
)


class BaseQueryParameters(Schema):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    @field_validator("*", mode="after")
    def convert_null_strings(value: Any) -> Any:  # noqa
        if isinstance(value, str) and value.lower() == "null":
            return None
        if isinstance(value, list):
            return [
                None if isinstance(v, str) and v.lower() == "null" else v for v in value
            ]
        return value


class CollectionQueryParameters(BaseQueryParameters):
    page: Optional[int] = Query(None, ge=1, description="Page number (1-based).")
    page_size: Optional[int] = Query(
        None, ge=0, le=100000, description="The number of items per page."
    )


class VocabularyQueryParameters(CollectionQueryParameters):
    order_desc: Optional[bool] = Query(
        False,
        description="Sort terms by descending.",
    )


class BaseGetResponse(Schema):
    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


class BasePostBody(Schema):
    @field_validator("*", mode="before")
    def empty_str_to_none(cls, value):
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


class BasePatchBody(Schema, metaclass=PartialSchema):
    @field_validator("*", mode="before")
    def empty_str_to_none(cls, value):
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )
