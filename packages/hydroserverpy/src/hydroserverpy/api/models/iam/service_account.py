from typing import Optional, Union, ClassVar, TYPE_CHECKING
from uuid import UUID
from datetime import datetime
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class ServiceAccount(HydroServerBaseModel):
    name: str
    email: str
    workspace_id: Union[UUID, str]
    description: Optional[str] = None
    is_active: bool
    key_expires_at: Optional[datetime] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None

    _editable_fields: ClassVar[set[str]] = {"name", "description", "is_active", "key_expires_at"}

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=None, **data)

        self._workspace = None

    @property
    def workspace(self) -> "Workspace":
        """The workspace this service account belongs to."""

        if self._workspace is None:
            self._workspace = self.client.workspaces.get(uid=self.workspace_id)

        return self._workspace

    def save(self):
        """Saves changes to this resource to HydroServer."""

        if not self.uid:
            raise AttributeError("Data cannot be saved: UID is not set.")

        if self.unsaved_changes:
            saved_resource = self.client.workspaces.update_service_account(
                uid=self.workspace_id, service_account_id=self.uid, **self.unsaved_changes
            )
            self._server_data = saved_resource.dict(by_alias=False).copy()
            self.__dict__.update(saved_resource.__dict__)

    def refresh(self):
        """Refreshes this resource from HydroServer."""

        if self.uid is None:
            raise ValueError("Cannot refresh data without a valid ID.")

        refreshed_resource = self.client.workspaces.get_service_account(
            uid=self.workspace_id, service_account_id=self.uid
        )
        self._server_data = refreshed_resource.dict(by_alias=False).copy()
        self.__dict__.update(refreshed_resource.__dict__)

    def delete(self):
        """Deletes this resource from HydroServer."""

        if self.uid is None:
            raise AttributeError("Cannot delete data without a valid ID.")

        self.client.workspaces.delete_service_account(
            uid=self.workspace_id, service_account_id=self.uid
        )
        self.uid = None

    def regenerate(self) -> str:
        """Regenerates this service account's key. WARNING: the previous key will be invalidated."""

        _, key = self.client.workspaces.regenerate_service_account_key(
            uid=self.workspace_id, service_account_id=self.uid
        )

        return key
