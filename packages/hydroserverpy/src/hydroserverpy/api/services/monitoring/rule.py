import json
from datetime import datetime
from typing import List, Literal, Optional, Union, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models.monitoring.rule import MonitoringRule
from hydroserverpy.api.models.base import HydroServerCollection
from hydroserverpy.api.utils import normalize_uuid, order_by_to_camel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class MonitoringRuleService:
    def __init__(self, client: "HydroServer"):
        self.client = client
        self.model = MonitoringRule

    @staticmethod
    def default_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    def _task_route(self, task_id: Union[UUID, str]) -> str:
        return f"/{self.client.base_route}/monitoring/tasks/{str(task_id)}/rules"

    def list(
        self,
        task_id: Union[UUID, str],
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        datastream: Optional[Union[UUID, str]] = ...,
        rule_type: str = ...,
        fetch_all: bool = False,
    ) -> HydroServerCollection:
        """Fetch a collection of rules for a monitoring task."""

        params = {
            "page": page,
            "page_size": page_size,
            "order_by": [order_by_to_camel(o) for o in order_by] if order_by is not ... else order_by,
            "datastream_id": normalize_uuid(datastream),
            "rule_type": rule_type,
        }
        params = {k: ("null" if v is None else v) for k, v in params.items() if v is not ...}

        response = self.client.request("get", self._task_route(task_id), params=params)

        collection = HydroServerCollection(
            model=self.model,
            client=self.client,
            service=self,
            response=response,
            order_by=params.get("order_by"),
            filters={"task_id": task_id},
        )

        if fetch_all:
            collection = collection.fetch_all()

        return collection

    def get(self, task_id: Union[UUID, str], uid: Union[UUID, str]) -> MonitoringRule:
        """Fetch a single monitoring rule."""

        path = f"{self._task_route(task_id)}/{str(uid)}"
        response = self.client.request("get", path).json()

        return MonitoringRule(client=self.client, task_id=task_id, **response)

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
            "datastreamId": normalize_uuid(datastream),
            "ruleType": rule_type,
            "minValue": min_value,
            "maxValue": max_value,
            "windowInterval": window_interval,
            "windowIntervalUnits": window_interval_units,
        }
        if uid is not None:
            body["id"] = normalize_uuid(uid)

        response = self.client.request(
            "post",
            self._task_route(task_id),
            headers={"Content-type": "application/json"},
            data=json.dumps(body, default=self.default_serializer),
        ).json()

        return MonitoringRule(client=self.client, task_id=task_id, **response)

    def update(
        self,
        task_id: Union[UUID, str],
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
        body = {k: v for k, v in body.items() if v is not ...}

        response = self.client.request(
            "patch",
            f"{self._task_route(task_id)}/{str(uid)}",
            headers={"Content-type": "application/json"},
            data=json.dumps(body, default=self.default_serializer),
        ).json()

        return MonitoringRule(client=self.client, task_id=task_id, **response)

    def delete(self, task_id: Union[UUID, str], uid: Union[UUID, str]) -> None:
        """Delete a monitoring rule."""

        self.client.request("delete", f"{self._task_route(task_id)}/{str(uid)}")
