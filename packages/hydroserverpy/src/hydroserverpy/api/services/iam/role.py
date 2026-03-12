from typing import TYPE_CHECKING, Union, List, Optional
from uuid import UUID
from hydroserverpy.api.models import Role
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService


if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class RoleService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = Role
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Optional[Union["Workspace", UUID, str]] = ...,
        is_user_role: bool = ...,
        is_apikey_role: bool = ...,
        fetch_all: bool = False,
    ) -> List["Role"]:
        """Fetch a collection of HydroServer roles."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            fetch_all=fetch_all,
            workspace_id=normalize_uuid(workspace),
            is_user_role=is_user_role,
            is_apikey_role=is_apikey_role,
        )
