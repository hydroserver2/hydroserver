import copy
from enum import Enum, EnumMeta
from typing import Optional, Any, Union, Annotated
from ninja import Schema, Query
from pydantic import AliasGenerator, AliasChoices, ConfigDict, field_validator
from pydantic.alias_generators import to_camel

from core.types import Unset

base_alias_generator = AliasGenerator(
    serialization_alias=lambda field_name: to_camel(field_name),
    validation_alias=lambda field_name: AliasChoices(to_camel(field_name), field_name),
)


class OrderByMeta(EnumMeta):
    def __new__(mcs, name, bases, namespace):
        for key in list(namespace._member_names):  # noqa
            api_name, orm_field = namespace[key]
            namespace[f"{key}_desc"] = (f"-{api_name}", f"-{orm_field}")

        return super().__new__(mcs, name, bases, namespace)


class OrderByField(str, Enum, metaclass=OrderByMeta):
    def __new__(cls, api_name: str, orm_field: str):
        obj = str.__new__(cls, api_name)
        obj._value_ = api_name
        obj.orm_field = orm_field

        return obj


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
    page: Optional[int] = Query(1, ge=1, description="Page number (1-based).")
    page_size: Optional[int] = Query(
        100, ge=0, le=100000, description="The number of items per page."
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
        if isinstance(value, str) and value == "":
            return None
        return value

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


class PartialMetaclass(type(Schema)):
    """
    Metaclass for creating "partial" schemas.

    Marks all fields as `Unset` by default, necessary for PATCH operations where only provided fields should
    be included, or responses where a subset of fields is selected by the client. Copies all inherited model fields and
    annotations to avoid mutating base classes.
    """

    def __new__(
        cls, name: str, bases: tuple[type, ...], attrs: dict, **kwargs
    ) -> "PartialMetaclass":
        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)

        # `model_fields` is a deprecated read-only property that proxies
        # `__pydantic_fields__`. Assigning to it doesn't update the real
        # field store - it just adds a plain dict entry to this class's own
        # `__dict__`, which then shadows `BaseModel`'s `model_fields`
        # property for every subclass that lists this class earlier in its
        # MRO than the mixins it's meant to combine with (e.g. a
        # `*PatchBody(BasePatchBody, SomeFields, ...)` subclass would read
        # back the shadowed dict left behind here instead of the fields
        # merged in from `SomeFields`). Read and write `__pydantic_fields__`
        # directly so field mutations survive multi-inheritance.
        fields = {
            k: copy.deepcopy(v) for k, v in new_cls.__pydantic_fields__.items()
        }

        for field in fields.values():
            field.default = Unset

            metadata = field.metadata
            original_annotation = field.annotation

            if metadata:
                constrained_arm = Annotated[original_annotation, *metadata]
                field.metadata = []
            else:
                constrained_arm = original_annotation

            field.annotation = Union[constrained_arm, type(Unset)]

        new_cls.__pydantic_fields__ = fields
        new_cls.model_rebuild(force=True)  # noqa

        return new_cls


class BasePatchBody(Schema, metaclass=PartialMetaclass):
    @field_validator("*", mode="before")
    def empty_str_to_none(cls, value):
        if isinstance(value, str) and value == "":
            return None
        return value

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )
