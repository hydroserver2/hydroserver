from typing import List, Optional, Union, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models.etl.mapping import EtlMapping
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class EtlMappingService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = EtlMapping
        super().__init__(client)

    def list(
        self,
        etl_task: Optional[Union[UUID, str]] = ...,
        workspace: Optional[Union[UUID, str]] = ...,
        offset: int = ...,
        limit: int = ...,
        order_by: List[str] = ...,
        source_identifier: str = ...,
        fetch_all: bool = False,
    ):
        """Fetch a collection of ETL mappings."""

        return super().list(
            offset=offset,
            limit=limit,
            order_by=order_by,
            fetch_all=fetch_all,
            etl_task_id=normalize_uuid(etl_task),
            workspace_id=normalize_uuid(workspace),
            source_identifier=source_identifier,
        )

    def create(
        self,
        task_id: Union[UUID, str],
        source_identifier: str,
        target_datastream: Union[UUID, str],
        uid: Optional[UUID] = None,
    ) -> EtlMapping:
        """Create a new ETL mapping."""

        body = {
            "etlTaskId": normalize_uuid(task_id),
            "sourceIdentifier": source_identifier,
            "targetDatastreamId": normalize_uuid(target_datastream),
        }
        if uid is not None:
            body["id"] = normalize_uuid(uid)

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        source_identifier: str = ...,
        target_datastream: Union[UUID, str] = ...,
    ) -> EtlMapping:
        """Update an ETL mapping."""

        body = {
            "sourceIdentifier": source_identifier,
            "targetDatastreamId": normalize_uuid(target_datastream),
        }

        return super().update(uid=str(uid), **body)
