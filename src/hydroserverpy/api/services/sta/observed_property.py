from typing import Optional, Union, List, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models import ObservedProperty
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace, Thing, Datastream


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
        thing: Optional[Union["Thing", UUID, str]] = ...,
        datastream: Optional[Union["Datastream", UUID, str]] = ...,
        observed_property_type: str = ...,
        fetch_all: bool = False,
    ) -> List["ObservedProperty"]:
        """Fetch a collection of observed properties."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            workspace_id=normalize_uuid(workspace),
            thing_id=normalize_uuid(thing),
            datastream_id=normalize_uuid(datastream),
            type=observed_property_type,
            fetch_all=fetch_all,
        )

    def create(
        self,
        name: str,
        definition: str,
        description: str,
        observed_property_type: str,
        code: str,
        workspace: Optional[Union["Workspace", UUID, str]] = None,
        uid: Optional[UUID] = None
    ) -> "ObservedProperty":
        """Create a new observed property."""

        body = {
            "id": normalize_uuid(uid),
            "name": name,
            "definition": definition,
            "description": description,
            "type": observed_property_type,
            "code": code,
            "workspaceId": normalize_uuid(workspace),
        }

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        name: str = ...,
        definition: str = ...,
        description: str = ...,
        observed_property_type: str = ...,
        code: str = ...,
    ) -> "ObservedProperty":
        """Update an observed property."""

        body = {
            "name": name,
            "definition": definition,
            "description": description,
            "observedPropertyType": observed_property_type,
            "code": code,
        }

        return super().update(uid=str(uid), **body)
