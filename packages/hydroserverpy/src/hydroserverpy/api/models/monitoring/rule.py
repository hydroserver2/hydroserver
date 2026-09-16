import uuid
from datetime import datetime
from typing import ClassVar, Literal, Optional, TYPE_CHECKING
from pydantic import AliasChoices, AliasPath, Field
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class MonitoringRule(HydroServerBaseModel):
    task_id: uuid.UUID = Field(validation_alias="taskId")
    datastream_id: uuid.UUID = Field(
        validation_alias=AliasChoices("datastreamId", AliasPath("datastream", "id"))
    )
    rule_type: Literal["range", "rate_of_change", "persistence", "missing_data"]
    last_checked_at: Optional[datetime] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    window_interval: Optional[int] = None
    window_interval_units: Optional[Literal["minutes", "hours", "days"]] = None

    _editable_fields: ClassVar[set[str]] = {
        "min_value",
        "max_value",
        "window_interval",
        "window_interval_units",
    }

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.monitoringrules, **data)

    @classmethod
    def get_route(cls):
        return "monitoring-rules"
