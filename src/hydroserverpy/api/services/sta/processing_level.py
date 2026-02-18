from typing import Optional, Union, List, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models import ProcessingLevel
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace, Thing, Datastream


class ProcessingLevelService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = ProcessingLevel
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Optional[Union["Workspace", UUID, str]] = ...,
        thing: Optional[Union["Thing", UUID, str]] = ...,
        datastream: Optional[Union["Datastream", UUID, str]] = ...,
        fetch_all: bool = False,
    ) -> List["ProcessingLevel"]:
        """Fetch a collection of processing levels."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            workspace_id=normalize_uuid(workspace),
            thing_id=normalize_uuid(thing),
            datastream_id=normalize_uuid(datastream),
            fetch_all=fetch_all,
        )

    def create(
        self,
        code: str,
        definition: Optional[str] = None,
        explanation: Optional[str] = None,
        workspace: Optional[Union["Workspace", UUID, str]] = None,
        uid: Optional[UUID] = None,
    ) -> "ProcessingLevel":
        """Create a new processing level."""

        body = {
            "id": normalize_uuid(uid),
            "code": code,
            "definition": definition,
            "explanation": explanation,
            "workspaceId": normalize_uuid(workspace),
        }

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        code: str = ...,
        definition: str = ...,
        explanation: str = ...,
    ) -> "ProcessingLevel":
        """Update a processing level."""

        body = {
            "code": code,
            "definition": definition,
            "explanation": explanation,
        }

        return super().update(uid=str(uid), **body)
