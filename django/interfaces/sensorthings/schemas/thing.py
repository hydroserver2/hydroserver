from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional
from .workspace import WorkspaceProperties


class ThingProperties(BaseModel):
    sampling_feature_type: str
    sampling_feature_code: str
    site_type: str
    data_disclaimer: Optional[str] = None
    is_private: bool
    workspace: WorkspaceProperties
    file_attachments: dict[str, str]
    tags: dict[str, str]

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )
