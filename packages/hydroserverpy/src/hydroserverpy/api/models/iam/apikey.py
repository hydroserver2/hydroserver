from typing import Optional, Union, ClassVar, TYPE_CHECKING
from uuid import UUID
from datetime import datetime
from hydroserverpy.api.models.iam.role import Role
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class APIKey(HydroServerBaseModel):
    name: str
    role_id: Union[UUID, str]
    workspace_id: Union[UUID, str]
    description: Optional[str] = None
    is_active: bool
    expires_at: Optional[datetime] = None

    _editable_fields: ClassVar[set[str]] = {"name", "description", "role_id", "is_active", "expires_at"}

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=None, **data)

        self._workspace = None
        self._role = None

    @property
    def workspace(self) -> "Workspace":
        """The workspace this API key belongs to."""

        if self._workspace is None:
            self._workspace = self.client.workspaces.get(uid=self.workspace_id)

        return self._workspace

    @property
    def role(self) -> "Role":
        """The role this API key is assigned."""

        if self._role is None:
            self._role = self.client.roles.get(uid=self.role_id)

        return self._role

    @role.setter
    def role(self, role: Union["Role", UUID, str] = ...):
        if not role:
            raise ValueError("Role of API key cannot be None.")
        if normalize_uuid(role) != str(self.role_id):
            self.role_id = normalize_uuid(role)
            self._role = None

    def save(self):
        """Saves changes to this resource to HydroServer."""

        if not self.uid:
            raise AttributeError("Data cannot be saved: UID is not set.")

        if self.unsaved_changes:
            saved_resource = self.client.workspaces.update_api_key(
                uid=self.workspace_id, api_key_id=self.uid, **self.unsaved_changes
            )
            self._server_data = saved_resource.dict(by_alias=False).copy()
            self.__dict__.update(saved_resource.__dict__)

    def refresh(self):
        """Refreshes this resource from HydroServer."""

        if self.uid is None:
            raise ValueError("Cannot refresh data without a valid ID.")

        refreshed_resource = self.client.workspaces.get_api_key(uid=self.workspace_id, api_key_id=self.uid)
        self._server_data = refreshed_resource.dict(by_alias=False).copy()
        self.__dict__.update(refreshed_resource.__dict__)

    def delete(self):
        """Deletes this resource from HydroServer."""

        if self.uid is None:
            raise AttributeError("Cannot delete data without a valid ID.")

        self.client.workspaces.delete_api_key(
            uid=self.workspace_id, api_key_id=self.uid
        )
        self.uid = None

    def regenerate(self):
        """Regenerates this API key. WARNING: Previous key will be invalidated."""

        _, key = self.client.workspaces.regenerate_api_key(
            uid=self.workspace_id, api_key_id=self.uid
        )

        return key
