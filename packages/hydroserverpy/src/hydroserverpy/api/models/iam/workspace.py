from typing import List, Union, Optional, ClassVar, TYPE_CHECKING
from uuid import UUID
from datetime import datetime
from pydantic import Field, EmailStr, AliasPath
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import (
        Role,
        Collaborator,
        APIKey,
        Account,
        Thing,
        ObservedProperty,
        Sensor,
        Unit,
        ProcessingLevel,
        ResultQualifier,
        Datastream,
        OrchestrationSystem,
        Task,
        DataConnection,
    )


class Workspace(HydroServerBaseModel):
    name: str = Field(..., max_length=255)
    is_private: bool
    owner: "Account"
    collaborator_role_id: Optional[Union[UUID, str]] = Field(
        None, validation_alias=AliasPath("collaboratorRole", "id")
    )
    pending_transfer_to: Optional["Account"] = None

    _editable_fields: ClassVar[set[str]] = {"name", "is_private"}

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.workspaces, **data)

        self._roles = None
        self._collaborators = None
        self._collaborator_role = None
        self._apikeys = None
        self._things = None
        self._observedproperties = None
        self._processinglevels = None
        self._resultqualifiers = None
        self._units = None
        self._sensors = None
        self._datastreams = None
        self._orchestrationsystems = None
        self._dataconnections = None
        self._tasks = None

    @classmethod
    def get_route(cls):
        return "workspaces"

    @property
    def roles(self) -> List["Role"]:
        """The roles that can be assigned for this workspace."""

        if self._roles is None:
            self._roles = self.client.roles.list(workspace=self.uid, fetch_all=True).items

        return self._roles

    @property
    def collaborators(self) -> List["Collaborator"]:
        """The collaborators associated with this workspace."""

        if self._collaborators is None:
            self._collaborators = self.client.workspaces.list_collaborators(uid=self.uid)

        return self._collaborators

    @property
    def collaborator_role(self) -> Optional["Role"]:
        """The user's collaborator role on this workspace."""

        if self._collaborator_role is None and self.collaborator_role_id is not None:
            self._collaborator_role = self.client.roles.get(uid=self.collaborator_role_id)

        return self._collaborator_role

    @property
    def apikeys(self) -> List["APIKey"]:
        """The API keys associated with this workspace."""

        if self._apikeys is None:
            self._apikeys = self.client.workspaces.list_api_keys(uid=self.uid)

        return self._apikeys

    @property
    def things(self) -> List["Thing"]:
        """The things associated with this workspace."""

        if self._things is None:
            self._things = self.client.things.list(workspace=self.uid, fetch_all=True).items

        return self._things

    @property
    def observedproperties(self) -> List["ObservedProperty"]:
        """The observed properties associated with this workspace."""

        if self._observedproperties is None:
            self._observedproperties = self.client.observedproperties.list(workspace=self.uid, fetch_all=True).items

        return self._observedproperties

    @property
    def processinglevels(self) -> List["ProcessingLevel"]:
        """The processing levels associated with this workspace."""

        if self._processinglevels is None:
            self._processinglevels = self.client.processinglevels.list(workspace=self.uid, fetch_all=True).items

        return self._processinglevels

    @property
    def resultqualifiers(self) -> List["ResultQualifier"]:
        """The result qualifiers associated with this workspace."""

        if self._resultqualifiers is None:
            self._resultqualifiers = self.client.resultqualifiers.list(workspace=self.uid, fetch_all=True).items

        return self._resultqualifiers

    @property
    def units(self) -> List["Unit"]:
        """The units associated with this workspace."""

        if self._units is None:
            self._units = self.client.units.list(workspace=self.uid, fetch_all=True).items

        return self._units

    @property
    def sensors(self) -> List["Sensor"]:
        """The sensors associated with this workspace."""

        if self._sensors is None:
            self._sensors = self.client.sensors.list(workspace=self.uid, fetch_all=True).items

        return self._sensors

    @property
    def datastreams(self) -> List["Datastream"]:
        """The datastreams associated with this workspace."""

        if self._datastreams is None:
            self._datastreams = self.client.datastreams.list(workspace=self.uid, fetch_all=True).items

        return self._datastreams

    @property
    def orchestrationsystems(self) -> List["OrchestrationSystem"]:
        """The orchestration systems associated with this workspace."""

        if self._orchestrationsystems is None:
            self._orchestrationsystems = self.client.orchestrationsystems.list(workspace=self.uid, fetch_all=True).items

        return self._orchestrationsystems

    @property
    def dataconnections(self) -> List["DataConnection"]:
        """The ETL data connections associated with this workspace."""

        if self._dataconnections is None:
            self._dataconnections = self.client.dataconnections.list(workspace=self.uid, fetch_all=True).items

        return self._dataconnections

    @property
    def tasks(self) -> List["Task"]:
        """The ETL tasks associated with this workspace."""

        if self._tasks is None:
            self._tasks = self.client.tasks.list(workspace=self.uid, fetch_all=True).items

        return self._tasks

    def create_api_key(
        self,
        role: Union["Role", UUID, str],
        name: str,
        description: Optional[str] = None,
        is_active: bool = True,
        expires_at: Optional[datetime] = None
    ):
        """Create an API key associated with this workspace."""

        response, key = self.client.workspaces.create_api_key(
            uid=self.uid,
            role=role,
            name=name,
            description=description,
            is_active=is_active,
            expires_at=expires_at
        )
        self._apikeys = None

        return response, key

    def update_api_key(
        self,
        api_key_id: Union[UUID, str],
        role: Union["Role", UUID, str] = ...,
        name: str = ...,
        description: Optional[str] = ...,
        is_active: bool = ...,
        expires_at: Optional[datetime] = ...
    ):
        """Create an API key associated with this workspace."""

        response = self.client.workspaces.update_api_key(
            uid=self.uid,
            api_key_id=api_key_id,
            role=role,
            name=name,
            description=description,
            is_active=is_active,
            expires_at=expires_at
        )
        self._apikeys = None

        return response

    def delete_api_key(self, api_key_id: Union[UUID, str]):
        """Delete an API key associated with this workspace."""

        self.client.workspaces.delete_api_key(
            uid=self.uid,
            api_key_id=api_key_id
        )
        self._apikeys = None

    def regenerate_api_key(self, api_key_id: Union[UUID, str]):
        """Regenerate an API key associated with this workspace."""

        api_key, key = self.client.workspaces.regenerate_api_key(
            uid=self.uid,
            api_key_id=api_key_id
        )

        return api_key, key

    def add_collaborator(
        self, email: EmailStr, role: Union["Role", UUID, str]
    ) -> "Collaborator":
        """Add a new collaborator to the workspace."""

        response = self.client.workspaces.add_collaborator(
            uid=self.uid, email=email, role=role
        )
        self._collaborators = None

        return response

    def edit_collaborator_role(
        self, email: EmailStr, role: Union["Role", UUID, str]
    ) -> "Collaborator":
        """Edit a collaborator's role in this workspace."""

        response = self.client.workspaces.edit_collaborator_role(
            uid=self.uid, email=email, role=role
        )
        self._collaborators = None

        return response

    def remove_collaborator(self, email: EmailStr) -> None:
        """Remove a collaborator from the workspace."""

        self.client.workspaces.remove_collaborator(uid=self.uid, email=email)
        self._collaborators = None

    def transfer_ownership(self, email: EmailStr) -> None:
        """Transfer ownership of this workspace to another HydroServer user."""

        self.client.workspaces.transfer_ownership(uid=self.uid, email=email)
        self.refresh()

    def accept_ownership_transfer(self) -> None:
        """Accept ownership transfer of this workspace."""

        self.client.workspaces.accept_ownership_transfer(uid=self.uid)
        self.refresh()

    def cancel_ownership_transfer(self) -> None:
        """Cancel ownership transfer of this workspace."""

        self.client.workspaces.cancel_ownership_transfer(uid=self.uid)
        self.refresh()
