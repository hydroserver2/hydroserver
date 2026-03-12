from typing import Optional, Union, List, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models import ResultQualifier
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class ResultQualifierService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = ResultQualifier
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Optional[Union["Workspace", UUID, str]] = ...,
        fetch_all: bool = False,
    ) -> List["ResultQualifier"]:
        """Fetch a collection of result qualifiers."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            workspace_id=normalize_uuid(workspace),
            fetch_all=fetch_all,
        )

    def create(
        self,
        code: str,
        description: Optional[str] = None,
        workspace: Optional[Union["Workspace", UUID, str]] = None,
        uid: Optional[UUID] = None,
    ) -> "ResultQualifier":
        """Create a new result qualifier."""

        body = {
            "id": normalize_uuid(uid),
            "code": code,
            "description": description,
            "workspaceId": normalize_uuid(workspace),
        }

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        code: str = ...,
        description: str = ...,
    ) -> "ResultQualifier":
        """Update a result qualifier."""

        body = {
            "code": code,
            "description": description,
        }

        return super().update(uid=str(uid), **body)
