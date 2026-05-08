from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from uuid import UUID


class WorkspaceProperties(BaseModel):
    id: UUID
    name: str
    link: str
    is_private: bool

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )
