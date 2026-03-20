from typing import Optional, Union, TYPE_CHECKING
from uuid import UUID
from pydantic import Field
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class Role(HydroServerBaseModel):
    name: str = Field(..., max_length=255)
    description: str
    workspace_id: Optional[Union[UUID, str]] = None

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.workspaces, **data)

        self._workspace = None

    @classmethod
    def get_route(cls):
        return "roles"

    @property
    def workspace(self) -> "Workspace":
        """The workspace this role belongs to."""

        if self._workspace is None and self.workspace_id is not None:
            self._workspace = self.client.workspaces.get(uid=self.workspace_id)

        return self._workspace

    def save(self):
        raise NotImplementedError("Editing roles not enabled.")

    def delete(self):
        raise NotImplementedError("Deleting roles not enabled.")
