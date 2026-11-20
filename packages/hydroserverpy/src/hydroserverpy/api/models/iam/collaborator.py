from typing import Optional, Union, ClassVar, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models.iam.role import Role
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models.iam.workspace import Workspace


class Collaborator(HydroServerBaseModel):
    role_id: Union[UUID, str]
    workspace_id: Union[UUID, str]
    user_email: Optional[str] = None
    service_account_email: Optional[str] = None

    _editable_fields: ClassVar[set[str]] = {"role_id"}

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=None, **data)

        self._workspace = None
        self._role = None

    @property
    def email(self) -> str:
        """The email identifying whichever principal (user or service account) this collaborator is."""

        return self.user_email or self.service_account_email

    @property
    def is_service_account(self) -> bool:
        """Whether this collaborator is a service account rather than a user."""

        return self.service_account_email is not None

    @property
    def workspace(self) -> "Workspace":
        """The workspace this collaborator belongs to."""

        if self._workspace is None:
            self._workspace = self.client.workspaces.get(uid=self.workspace_id)

        return self._workspace

    @property
    def role(self) -> "Role":
        """The role this collaborator is assigned."""

        if self._role is None:
            self._role = self.client.roles.get(uid=self.role_id)

        return self._role

    @role.setter
    def role(self, role: Union["Role", UUID, str] = ...):
        if not role:
            raise ValueError("Role of collaborator cannot be None.")
        if normalize_uuid(role) != str(self.role_id):
            self.role_id = normalize_uuid(role)
            self._role = None

    def save(self):
        """Saves changes to this resource to HydroServer."""

        if self.unsaved_changes:
            saved = self.client.workspaces.edit_collaborator_role(
                uid=str(self.workspace_id), email=self.email, role=self.role_id
            )
            self._role = None
            self._server_data["role_id"] = self.role_id
            self.__dict__.update({"role_id": self.role_id})
            if saved is not None:
                self.__dict__.update(saved.__dict__)

    def delete(self):
        """Deletes this resource from HydroServer."""

        self.client.workspaces.remove_collaborator(
            uid=str(self.workspace_id), email=self.email
        )
        self.uid = None
