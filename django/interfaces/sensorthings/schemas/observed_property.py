from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional
from .workspace import WorkspaceProperties


class ObservedPropertyProperties(BaseModel):
    variable_code: str
    variable_type: str
    workspace: Optional[WorkspaceProperties] = None

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )
