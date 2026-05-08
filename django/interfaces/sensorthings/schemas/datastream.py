from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional, Literal
from uuid import UUID
from .workspace import WorkspaceProperties


class DatastreamProperties(BaseModel):
    result_type: str
    status: Optional[str] = None
    sampled_medium: str
    value_count: Optional[int] = None
    no_data_value: float
    processing_level_code: str
    processing_level_id: UUID
    unit_id: UUID
    intended_time_spacing: Optional[float] = None
    intended_time_spacing_unit_of_measurement: Optional[
        Literal["seconds", "minutes", "hours", "days"]
    ] = None
    aggregation_statistic: Optional[str] = None
    time_aggregation_interval: float
    time_aggregation_interval_unit_of_measurement: Literal[
        "seconds", "minutes", "hours", "days"
    ]
    is_private: bool
    is_visible: bool
    workspace: WorkspaceProperties
    file_attachments: dict[str, str]
    tags: dict[str, str]

    model_config = ConfigDict(
        populate_by_name=True, str_strip_whitespace=True, alias_generator=to_camel
    )
