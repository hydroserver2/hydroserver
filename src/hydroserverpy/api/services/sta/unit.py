from typing import Optional, Union, List, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models import Unit
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace, Thing, Datastream


class UnitService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = Unit
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Union["Workspace", UUID, str] = ...,
        thing: Optional[Union["Thing", UUID, str]] = ...,
        datastream: Optional[Union["Datastream", UUID, str]] = ...,
        unit_type: str = ...,
        fetch_all: bool = False,
    ) -> List["Unit"]:
        """Fetch a collection of units."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            workspace_id=normalize_uuid(workspace),
            thing_id=normalize_uuid(thing),
            datastream_id=normalize_uuid(datastream),
            unit_type=unit_type,
            fetch_all=fetch_all,
        )

    def create(
        self,
        name: str,
        symbol: str,
        definition: str,
        unit_type: str,
        workspace: Optional[Union["Workspace", UUID, str]] = None,
        uid: Optional[UUID] = None
    ) -> "Unit":
        """Create a new unit."""

        body = {
            "id": normalize_uuid(uid),
            "name": name,
            "symbol": symbol,
            "definition": definition,
            "type": unit_type,
            "workspaceId": normalize_uuid(workspace),
        }

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        name: str = ...,
        symbol: str = ...,
        definition: str = ...,
        unit_type: str = ...,
    ) -> "Unit":
        """Update a unit."""

        body = {
            "name": name,
            "symbol": symbol,
            "definition": definition,
            "type": unit_type,
        }

        return super().update(uid=str(uid), **body)
