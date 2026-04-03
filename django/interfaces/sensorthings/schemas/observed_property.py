from ninja import Schema
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional
from sensorthings.components.observedproperties.schemas import (
    ObservedPropertyGetResponse as DefaultObservedPropertyGetResponse,
    ObservedPropertyListResponse as DefaultObservedPropertyListResponse,
)
from .workspace import WorkspaceProperties


class ObservedPropertyProperties(Schema):
    variable_code: str
    variable_type: str
    workspace: Optional[WorkspaceProperties] = None

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )


class ObservedPropertyGetResponse(DefaultObservedPropertyGetResponse):
    definition: str
    properties: ObservedPropertyProperties


class ObservedPropertyListResponse(DefaultObservedPropertyListResponse):
    value: list[ObservedPropertyGetResponse]
