import json
from typing import List, Optional, Union, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models.etl.mapping import EtlMapping
from hydroserverpy.api.models.base import HydroServerCollection
from hydroserverpy.api.utils import normalize_uuid, sortby_to_camel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class EtlMappingService:
    def __init__(self, client: "HydroServer"):
        self.client = client
        self.model = EtlMapping

    def _task_route(self, task_id: Union[UUID, str]) -> str:
        return f"/{self.client.base_route}/etl/tasks/{str(task_id)}/mappings"

    def list(
        self,
        task_id: Union[UUID, str],
        offset: int = ...,
        limit: int = ...,
        sortby: List[str] = ...,
        source_identifier: str = ...,
        fetch_all: bool = False,
    ) -> HydroServerCollection:
        """Fetch a collection of mappings for an ETL task."""

        params = {
            "offset": offset,
            "limit": limit,
            "sortby": [sortby_to_camel(o) for o in sortby] if sortby is not ... else sortby,
            "source_identifier": source_identifier,
        }
        params = {k: ("null" if v is None else v) for k, v in params.items() if v is not ...}

        response = self.client.request("get", self._task_route(task_id), params=params)

        items = [
            EtlMapping(client=self.client, task_id=task_id, **entity)
            for entity in response.json()["data"]
        ]

        collection = HydroServerCollection(
            model=self.model,
            client=self.client,
            service=self,
            response=response,
            sortby=params.get("sortby"),
            filters={"task_id": task_id},
            items=items,
        )

        if fetch_all:
            collection = collection.fetch_all()

        return collection

    def get(self, task_id: Union[UUID, str], uid: Union[UUID, str]) -> EtlMapping:
        """Fetch a single ETL mapping."""

        path = f"{self._task_route(task_id)}/{str(uid)}"
        payload = self.client.request("get", path).json()
        data = payload.get("data", payload)

        return EtlMapping(client=self.client, task_id=task_id, **data)

    def create(
        self,
        task_id: Union[UUID, str],
        source_identifier: str,
        target_datastream: Union[UUID, str],
        uid: Optional[UUID] = None,
    ) -> EtlMapping:
        """Create a new mapping on an ETL task."""

        body = {
            "sourceIdentifier": source_identifier,
            "targetDatastreamId": normalize_uuid(target_datastream),
        }
        if uid is not None:
            body["id"] = normalize_uuid(uid)

        response = self.client.request(
            "post",
            self._task_route(task_id),
            headers={"Content-type": "application/json"},
            data=json.dumps(body),
        ).json()

        return self.get(task_id=task_id, uid=response["id"])

    def update(
        self,
        task_id: Union[UUID, str],
        uid: Union[UUID, str],
        source_identifier: str = ...,
        target_datastream: Union[UUID, str] = ...,
    ) -> EtlMapping:
        """Update an ETL mapping."""

        body = {
            "sourceIdentifier": source_identifier,
            "targetDatastreamId": normalize_uuid(target_datastream) if target_datastream is not ... else ...,
        }
        body = {k: v for k, v in body.items() if v is not ...}

        self.client.request(
            "patch",
            f"{self._task_route(task_id)}/{str(uid)}",
            headers={"Content-type": "application/json"},
            data=json.dumps(body),
        )

        return self.get(task_id=task_id, uid=uid)

    def delete(self, task_id: Union[UUID, str], uid: Union[UUID, str]) -> None:
        """Delete an ETL mapping."""

        self.client.request("delete", f"{self._task_route(task_id)}/{str(uid)}")
