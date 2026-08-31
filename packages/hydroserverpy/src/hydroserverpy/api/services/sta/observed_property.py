from typing import Optional, Union, List, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models import ObservedProperty
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace, MonitoringSite, Datastream


class ObservedPropertyService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = ObservedProperty
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Optional[Union["Workspace", UUID, str]] = ...,
        monitoring_site: Optional[Union["MonitoringSite", UUID, str]] = ...,
        datastream: Optional[Union["Datastream", UUID, str]] = ...,
        type: str = ...,
        fetch_all: bool = False,
    ) -> List["ObservedProperty"]:
        """Fetch a collection of observed properties."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            workspace_id=normalize_uuid(workspace),
            monitoring_site_id=normalize_uuid(monitoring_site),
            datastream_id=normalize_uuid(datastream),
            type=type,
            fetch_all=fetch_all,
        )

    def create(
        self,
        name: str,
        description: str,
        type: str,
        code: str,
        definition: Optional[str] = None,
        workspace: Optional[Union["Workspace", UUID, str]] = None,
        uid: Optional[UUID] = None,
    ) -> "ObservedProperty":
        """Create a new observed property."""

        body = {
            "id": normalize_uuid(uid),
            "name": name,
            "definition": definition,
            "description": description,
            "type": type,
            "code": code,
            "workspaceId": normalize_uuid(workspace),
        }

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        name: str = ...,
        description: str = ...,
        type: str = ...,
        code: str = ...,
        definition: Optional[str] = ...,
    ) -> "ObservedProperty":
        """Update an observed property."""

        body = {
            "name": name,
            "definition": definition,
            "description": description,
            "type": type,
            "code": code,
        }

        return super().update(uid=str(uid), **body)
