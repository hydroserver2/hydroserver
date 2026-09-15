import copy
import uuid

from typing import Optional, Any, Union, Annotated, Generic, TypeVar, get_args
from ninja import Schema, Query
from pydantic.alias_generators import to_camel
from pydantic import (
    AliasGenerator,
    AliasChoices,
    ConfigDict,
    field_validator,
    model_serializer,
    SerializationInfo,
)

from core.types import Unset

base_alias_generator = AliasGenerator(
    serialization_alias=lambda field_name: to_camel(field_name),
    validation_alias=lambda field_name: AliasChoices(to_camel(field_name), field_name),
)


def split_comma_separated(value: Any) -> Optional[list[str]]:
    """
    Splits a given input into a list of non-empty, comma-separated strings.

    If the input is a string or an iterable, this function splits the elements
    by commas, trims any leading or trailing whitespaces, and filters out
    empty strings. Returns None if the input is None.
    """

    if value is None:
        return None

    parts = [value] if isinstance(value, str) else list(value)
    result: list[str] = []

    for part in parts:
        result.extend(p.strip() for p in part.split(",") if p.strip())

    return result


def comma_array_schema(literal_type: Any) -> dict:
    """
    Generates a JSON schema for an array of strings based on a given Python Literal type.

    This function is used to create a schema that defines an array of strings, where each string
    in the array is restricted to a specific predefined set of values, as determined by the provided
    Literal type.
    """

    return {
        "type": "array",
        "items": {"type": "string", "enum": list(get_args(literal_type))},
        "style": "form",
        "explode": False,
    }


def parse_requested_properties(info: SerializationInfo) -> Optional[set[str]]:
    """
    Parses and retrieves the requested properties from the serialization context.

    Extracts the "properties" parameter from the serialization context's request and
    converts it into a set of property names. If no properties are specified in the
    request, the function returns None.
    """

    request = (info.context or {}).get("request") if info.context else None
    query_dict = getattr(request, "GET", None) if request is not None else None
    raw_values = query_dict.getlist("properties") if query_dict is not None else []
    parsed = split_comma_separated(raw_values)

    if not parsed:
        return None

    return set(parsed)


def filter_requested_properties(item: Any, requested: set[str]) -> Any:
    """
    Filters properties of a dictionary based on a specified set of keys.

    This function takes a dictionary and a set of requested keys and returns a new dictionary
    containing only the key-value pairs where the key exists in the requested set. If the input
    item is not a dictionary, it is returned as is.
    """

    if not isinstance(item, dict):
        return item

    return {k: v for k, v in item.items() if k in requested}


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
    properties: Optional[str] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Optional[str] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )
    offset: Optional[int] = Query(0, ge=0, description="Number of items to skip.")
    limit: Optional[int] = Query(
        100, ge=0, le=100000, description="The maximum number of items to return."
    )


class VocabularyQueryParameters(CollectionQueryParameters):
    sort_desc: Optional[bool] = Query(
        False,
        description="Sort terms by descending.",
    )


class BaseGetResponse(Schema):
    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


class CreatedResponse(Schema):
    id: uuid.UUID

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class PaginationMeta(Schema):
    limit: int
    offset: int
    total_count: int

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


T = TypeVar("T")


class ItemResponse(Schema, Generic[T]):
    included: Optional[dict[str, list[Any]]] = None
    data: T

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    @model_serializer(mode="wrap")
    def _finalize(self, handler, info: SerializationInfo):
        data = handler(self)
        if not isinstance(data, dict):
            return data

        requested = parse_requested_properties(info)
        if requested is not None:
            data["data"] = filter_requested_properties(data.get("data"), requested)

        return data


class PaginatedResponse(Schema, Generic[T]):
    included: Optional[dict[str, list[Any]]] = None
    data: list[T]
    meta: PaginationMeta

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    @model_serializer(mode="wrap")
    def _finalize(self, handler, info: SerializationInfo):
        data = handler(self)
        if not isinstance(data, dict):
            return data

        if not data.get("included"):
            data.pop("included", None)

        requested = parse_requested_properties(info)
        if requested is not None and isinstance(data.get("data"), list):
            data["data"] = [filter_requested_properties(item, requested) for item in data["data"]]

        return data


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
        fields = {k: copy.deepcopy(v) for k, v in new_cls.model_fields.items()}

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

        # `model_fields` is a read-only view of `__pydantic_fields__` as of newer
        # pydantic versions, so the canonical field mapping must be updated directly
        # for schema regeneration to pick up the mutated defaults/annotations.
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
