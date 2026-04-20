import uuid
from datetime import datetime
from typing import ClassVar, Literal, Optional, TYPE_CHECKING
from pydantic import Field, AliasPath
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class MonitoringRule(HydroServerBaseModel):
    task_id: uuid.UUID
    datastream_id: uuid.UUID = Field(..., validation_alias=AliasPath("datastream", "id"))
    datastream_name: str = Field(..., validation_alias=AliasPath("datastream", "name"))
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

    def __init__(self, client: "HydroServer", task_id: uuid.UUID, **data):
        super().__init__(client=client, service=client.monitoring_rules, task_id=task_id, **data)

    @classmethod
    def get_route(cls):
        return "monitoring/rules"

    def save(self):
        """Save changes to this rule to HydroServer."""

        if self.unsaved_changes:
            saved = self.client.monitoring_rules.update(
                task_id=self.task_id, uid=self.uid, **self.unsaved_changes
            )
            self._server_data = saved.dict(by_alias=False).copy()
            self.__dict__.update(saved.__dict__)

    def delete(self):
        """Delete this rule from HydroServer."""

        self.client.monitoring_rules.delete(task_id=self.task_id, uid=self.uid)
        self.uid = None
