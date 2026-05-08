from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional
from .workspace import WorkspaceProperties


class LocationProperties(BaseModel):
    admin_area_1: Optional[str] = None
    admin_area_2: Optional[str] = None
    country: Optional[str] = None
    elevation_m: Optional[float] = Field(None, alias="elevation_m")
    elevation_datum: Optional[str] = None
    workspace: WorkspaceProperties

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )
