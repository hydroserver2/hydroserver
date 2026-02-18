from typing import Union, List, Optional, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models import OrchestrationSystem
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class OrchestrationSystemService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = OrchestrationSystem
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Union["Workspace", UUID, str] = ...,
        orchestration_system_type: str = ...,
        fetch_all: bool = False,
    ) -> List["OrchestrationSystem"]:
        """Fetch a collection of orchestration systems."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            workspace_id=normalize_uuid(workspace),
            type=orchestration_system_type,
            fetch_all=fetch_all,
        )

    def create(
        self,
        name: str,
        orchestration_system_type: str,
        workspace: Optional[Union["Workspace", UUID, str]] = None,
        uid: Optional[UUID] = None
    ) -> "OrchestrationSystem":
        """Create a new orchestration system."""

        body = {
            "id": normalize_uuid(uid),
            "name": name,
            "type": orchestration_system_type,
            "workspaceId": normalize_uuid(workspace),
        }

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        name: str = ...,
        orchestration_system_type: str = ...,
    ) -> "OrchestrationSystem":
        """Update an orchestration system."""

        body = {
            "name": name,
            "type": orchestration_system_type,
        }

        return super().update(uid=str(uid), **body)
