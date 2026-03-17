from ninja import Schema
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel
from uuid import UUID
from sensorthings.types import AnyHttpUrlString


class WorkspaceProperties(Schema):
    id: UUID
    name: str
    link: AnyHttpUrlString
    is_private: bool

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )
