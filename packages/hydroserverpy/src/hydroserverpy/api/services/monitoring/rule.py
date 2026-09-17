from typing import List, Literal, Optional, Union, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models.monitoring.rule import MonitoringRule
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class MonitoringRuleService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = MonitoringRule
        super().__init__(client)

    def list(
        self,
        task: Optional[Union[UUID, str]] = ...,
        workspace: Optional[Union[UUID, str]] = ...,
        offset: int = ...,
        limit: int = ...,
        order_by: List[str] = ...,
        datastream: Optional[Union[UUID, str]] = ...,
        rule_type: str = ...,
        fetch_all: bool = False,
    ):
        """Fetch a collection of monitoring rules."""

        return super().list(
            offset=offset,
            limit=limit,
            order_by=order_by,
            fetch_all=fetch_all,
            task_id=normalize_uuid(task),
            workspace_id=normalize_uuid(workspace),
            datastream_id=normalize_uuid(datastream),
            rule_type=rule_type,
        )

    def create(
        self,
        task_id: Union[UUID, str],
        datastream: Union[UUID, str],
        rule_type: Literal["range", "rate_of_change", "persistence", "missing_data"],
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        window_interval: Optional[int] = None,
        window_interval_units: Optional[Literal["minutes", "hours", "days"]] = None,
        uid: Optional[UUID] = None,
    ) -> MonitoringRule:
        """Create a new monitoring rule on a task."""

        body = {
            "taskId": normalize_uuid(task_id),
            "datastreamId": normalize_uuid(datastream),
            "ruleType": rule_type,
            "minValue": min_value,
            "maxValue": max_value,
            "windowInterval": window_interval,
            "windowIntervalUnits": window_interval_units,
        }
        if uid is not None:
            body["id"] = normalize_uuid(uid)

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        min_value: Optional[float] = ...,
        max_value: Optional[float] = ...,
        window_interval: Optional[int] = ...,
        window_interval_units: Optional[Literal["minutes", "hours", "days"]] = ...,
    ) -> MonitoringRule:
        """Update a monitoring rule's parameters."""

        body = {
            "minValue": min_value,
            "maxValue": max_value,
            "windowInterval": window_interval,
            "windowIntervalUnits": window_interval_units,
        }

        return super().update(uid=str(uid), **body)
