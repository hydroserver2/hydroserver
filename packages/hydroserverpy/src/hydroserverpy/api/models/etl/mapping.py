from typing import List
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class TaskMappingPath(BaseModel):
    target_identifier: str
    data_transformations: list = Field(default_factory=list)

    model_config = ConfigDict(
        validate_assignment=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        alias_generator=to_camel,
    )


class TaskMapping(BaseModel):
    source_identifier: str
    paths: List[TaskMappingPath]

    model_config = ConfigDict(
        validate_assignment=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        alias_generator=to_camel,
    )
