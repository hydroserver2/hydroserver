from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models.products.task import DataProductTask
from hydroserverpy.api.models.orchestration.run import TaskRun
from hydroserverpy.api.utils import normalize_uuid, order_by_to_camel
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class DataProductTaskService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = DataProductTask
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        thing: Optional[Union[UUID, str]] = ...,
        workspace: Optional[Union[UUID, str]] = ...,
        latest_run_status: str = ...,
        transformation_type: str = ...,
        output_datastream: Optional[Union[UUID, str]] = ...,
        input_datastream: Optional[Union[UUID, str]] = ...,
        rating_curve: Optional[Union[UUID, str]] = ...,
        fetch_all: bool = False,
    ) -> List[DataProductTask]:
        """Fetch a collection of data product tasks."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            fetch_all=fetch_all,
            thing_id=normalize_uuid(thing),
            workspace_id=normalize_uuid(workspace),
            latest_run_status=latest_run_status,
            transformation_type=transformation_type,
            output_datastream_id=normalize_uuid(output_datastream),
            input_datastream_id=normalize_uuid(input_datastream),
            rating_curve_id=normalize_uuid(rating_curve),
        )

    def create(
        self,
        name: str,
        thing: Union[UUID, str],
        description: Optional[str] = None,
        crontab: Optional[str] = None,
        interval: Optional[int] = None,
        interval_period: Optional[Literal["minutes", "hours", "days"]] = None,
        start_time: Optional[datetime] = None,
        enabled: bool = True,
        uid: Optional[UUID] = None,
    ) -> DataProductTask:
        """Create a new data product task."""

        body: Dict[str, Any] = {
            "name": name,
            "description": description,
            "thingId": normalize_uuid(thing),
        }

        if uid is not None:
            body["id"] = normalize_uuid(uid)

        if crontab or interval:
            body["schedule"] = {
                "enabled": enabled,
                "startTime": start_time,
                "crontab": crontab,
                "interval": interval,
                "intervalPeriod": interval_period,
            }

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        name: str = ...,
        description: Optional[str] = ...,
        crontab: Optional[str] = ...,
        interval: Optional[int] = ...,
        interval_period: Optional[Literal["minutes", "hours", "days"]] = ...,
        start_time: Optional[datetime] = ...,
        enabled: bool = ...,
    ) -> DataProductTask:
        """Update a data product task."""

        body: Dict[str, Any] = {
            "name": name,
            "description": description,
        }

        if crontab is None and interval is None:
            body["schedule"] = None
        elif any(v is not ... for v in [enabled, start_time, crontab, interval, interval_period]):
            body["schedule"] = {
                "enabled": enabled,
                "startTime": start_time,
                "crontab": crontab,
                "interval": interval,
                "intervalPeriod": interval_period,
            }

        return super().update(uid=str(uid), **body)

    def trigger(self, uid: Union[UUID, str]) -> TaskRun:
        """Trigger an immediate run of a data product task."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/trigger"
        response = self.client.request("post", path).json()

        return TaskRun(**response)

    def list_runs(
        self,
        uid: Union[UUID, str],
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        status: str = ...,
        started_at_min: datetime = ...,
        started_at_max: datetime = ...,
        finished_at_min: datetime = ...,
        finished_at_max: datetime = ...,
    ) -> List[TaskRun]:
        """Fetch a collection of task runs for a data product task."""

        params = {
            "page": page,
            "page_size": page_size,
            "order_by": [order_by_to_camel(o) for o in order_by] if order_by is not ... else order_by,
            "status": status,
            "started_at_min": started_at_min,
            "started_at_max": started_at_max,
            "finished_at_min": finished_at_min,
            "finished_at_max": finished_at_max,
        }
        params = {k: v for k, v in params.items() if v is not ...}

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/runs"

        return [TaskRun(**run) for run in self.client.request("get", path, params=params).json()]

    def get_run(self, uid: Union[UUID, str], run_id: Union[UUID, str]) -> TaskRun:
        """Fetch a single task run for a data product task."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/runs/{str(run_id)}"

        return TaskRun(**self.client.request("get", path).json())