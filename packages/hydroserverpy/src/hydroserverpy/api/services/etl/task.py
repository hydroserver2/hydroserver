from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models.etl.task import EtlTask
from hydroserverpy.api.models.orchestration.run import TaskRun
from hydroserverpy.api.utils import normalize_uuid, order_by_to_camel
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class TaskService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = EtlTask
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Optional[Union[UUID, str]] = ...,
        data_connection: Optional[Union[UUID, str]] = ...,
        latest_run_status: str = ...,
        latest_run_started_at_min: Optional[datetime] = ...,
        latest_run_started_at_max: Optional[datetime] = ...,
        latest_run_finished_at_min: Optional[datetime] = ...,
        latest_run_finished_at_max: Optional[datetime] = ...,
        fetch_all: bool = False,
    ) -> List[EtlTask]:
        """Fetch a collection of ETL tasks."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            fetch_all=fetch_all,
            workspace_id=normalize_uuid(workspace),
            data_connection_id=normalize_uuid(data_connection),
            latest_run_status=latest_run_status,
            latest_run_started_at_min=latest_run_started_at_min,
            latest_run_started_at_max=latest_run_started_at_max,
            latest_run_finished_at_min=latest_run_finished_at_min,
            latest_run_finished_at_max=latest_run_finished_at_max,
        )

    def create(
        self,
        name: str,
        data_connection: Union[UUID, str],
        description: Optional[str] = None,
        task_variables: Optional[Dict[str, Any]] = None,
        mappings: Optional[List[dict]] = None,
        crontab: Optional[str] = None,
        interval: Optional[int] = None,
        interval_period: Optional[Literal["minutes", "hours", "days"]] = None,
        start_time: Optional[datetime] = None,
        enabled: bool = True,
        uid: Optional[UUID] = None,
    ) -> EtlTask:
        """Create a new ETL task."""

        body: Dict[str, Any] = {
            "name": name,
            "description": description,
            "dataConnectionId": normalize_uuid(data_connection),
            "taskVariables": task_variables or {},
            "mappings": [
                {"sourceIdentifier": m.get("source_identifier") or m.get("sourceIdentifier"),
                 "targetDatastreamId": str(m.get("target_datastream_id") or m.get("targetDatastreamId"))}
                for m in (mappings or [])
            ],
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
        name: str,
        mappings: List[dict],
        description: Optional[str] = None,
        task_variables: Optional[Dict[str, Any]] = None,
        crontab: Optional[str] = ...,
        interval: Optional[int] = ...,
        interval_period: Optional[Literal["minutes", "hours", "days"]] = ...,
        start_time: Optional[datetime] = ...,
        enabled: bool = ...,
    ) -> EtlTask:
        """Update an ETL task."""

        body: Dict[str, Any] = {
            "name": name,
            "description": description,
            "taskVariables": task_variables or {},
            "mappings": [
                {"sourceIdentifier": m.get("source_identifier") or m.get("sourceIdentifier"),
                 "targetDatastreamId": str(m.get("target_datastream_id") or m.get("targetDatastreamId"))}
                for m in mappings
            ],
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
        """Trigger an immediate run of an ETL task."""

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
        """Fetch a collection of task runs for an ETL task."""

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
        """Fetch a single task run for an ETL task."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/runs/{str(run_id)}"

        return TaskRun(**self.client.request("get", path).json())