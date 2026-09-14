import json
from typing import TYPE_CHECKING, Optional, Union, List, Tuple
from pydantic import EmailStr
from uuid import UUID
from datetime import datetime
from hydroserverpy.api.models import Workspace, Role, Collaborator, ServiceAccount
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService


if TYPE_CHECKING:
    from hydroserverpy import HydroServer


def _resolve_email(email: Union[EmailStr, "ServiceAccount"]) -> str:
    return email.email if isinstance(email, ServiceAccount) else email


class WorkspaceService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = Workspace
        super().__init__(client)

    def list(
        self,
        offset: int = ...,
        limit: int = ...,
        order_by: List[str] = ...,
        is_private: bool = ...,
        is_associated: bool = ...,
        fetch_all: bool = False,
    ) -> List["Workspace"]:
        """Fetch a collection of HydroServer workspaces."""

        return super().list(
            offset=offset,
            limit=limit,
            order_by=order_by,
            fetch_all=fetch_all,
            is_private=is_private,
            is_associated=is_associated,
        )

    def create(
        self,
        name: str,
        is_private: bool,
        uid: Optional[UUID] = None,
        **_
    ) -> "Workspace":
        """Create a new workspace."""

        return super().create(
            id=normalize_uuid(uid),
            name=name,
            is_private=is_private,
        )

    def update(
        self, uid: Union[UUID, str], name: str = ..., is_private: bool = ..., **_
    ) -> "Workspace":
        """Update a workspace."""

        return super().update(
            uid=uid,
            name=name,
            is_private=is_private,
        )

    def list_collaborators(self, uid: Union[UUID, str]) -> List["Collaborator"]:
        """Get all collaborators associated with a workspace."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/collaborators"
        response = self.client.request("get", path)

        return [
            Collaborator(client=self.client, uid=None, workspace_id=uid, **obj)
            for obj in response.json()["data"]
        ]

    def add_collaborator(
        self, uid: Union[UUID, str], email: Union[EmailStr, "ServiceAccount"], role: Union["Role", UUID, str]
    ) -> "Collaborator":
        """Add a collaborator (a user or a service account) to a workspace."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/collaborators"
        headers = {"Content-type": "application/json"}
        resolved_email = _resolve_email(email)
        body = {
            "email": resolved_email,
            "roleId": normalize_uuid(role)
        }
        self.client.request(
            "post", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        )

        return next(
            (c for c in self.list_collaborators(uid) if c.email == resolved_email),
            None,
        )

    def edit_collaborator_role(
        self,
        uid: Union[UUID, str],
        email: Union[EmailStr, "ServiceAccount"],
        role: Union["Role", UUID, str] = ...,
        role_id: UUID = ...,
    ) -> "Collaborator":
        """Edit the role of a collaborator in a workspace."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/collaborators"
        headers = {"Content-type": "application/json"}
        resolved_email = _resolve_email(email)
        body = {
            "email": resolved_email,
            "roleId": normalize_uuid(role if role is not ... else role_id)
        }

        self.client.request(
            "put", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        )

        return next(
            (c for c in self.list_collaborators(uid) if c.email == resolved_email),
            None,
        )

    def remove_collaborator(self, uid: Union[UUID, str], email: Union[EmailStr, "ServiceAccount"]) -> None:
        """Remove a collaborator from a workspace."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/collaborators"
        self.client.request("delete", path, json={"email": _resolve_email(email)})

    def list_service_accounts(self, uid: Union[UUID, str]) -> List["ServiceAccount"]:
        """Get all service accounts associated with a workspace."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/service-accounts"
        response = self.client.request("get", path)

        return [
            ServiceAccount(client=self.client, **obj)
            for obj in response.json()["data"]
        ]

    def get_service_account(
        self, uid: Union[UUID, str], service_account_id: Union[UUID, str]
    ) -> "ServiceAccount":
        """Get a service account associated with a workspace."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/service-accounts/{service_account_id}"
        payload = self.client.request("get", path).json()

        return ServiceAccount(client=self.client, **payload.get("data", payload))

    def create_service_account(
        self,
        uid: Union[UUID, str],
        name: str,
        description: Optional[str] = None,
        is_active: bool = True,
        key_expires_at: Optional[datetime] = None,
        role: Optional[Union["Role", UUID, str]] = None,
    ) -> Tuple["ServiceAccount", str]:
        """Create a service account for a workspace."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/service-accounts"
        headers = {"Content-type": "application/json"}
        body = {
            "name": name,
            "description": description,
            "isActive": is_active,
            "keyExpiresAt": key_expires_at,
            "roleId": normalize_uuid(role) if role is not None else None,
        }

        response = self.client.request(
            "post", path, headers=headers, data=json.dumps(body, default=self.default_serializer),
        ).json()

        return self.get_service_account(uid, response["id"]), response["key"]

    def update_service_account(
        self,
        uid: Union[UUID, str],
        service_account_id: Union[UUID, str],
        name: str = ...,
        description: Optional[str] = ...,
        is_active: bool = ...,
        key_expires_at: Optional[datetime] = ...,
    ) -> "ServiceAccount":
        """Update an existing service account."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/service-accounts/{service_account_id}"
        headers = {"Content-type": "application/json"}
        body = {
            "name": name,
            "description": description,
            "isActive": is_active,
            "keyExpiresAt": key_expires_at,
        }
        body = {k: v for k, v in body.items() if v is not ...}

        self.client.request(
            "patch", path, headers=headers, data=json.dumps(body, default=self.default_serializer),
        )

        return self.get_service_account(uid, service_account_id)

    def delete_service_account(
        self,
        uid: Union[UUID, str],
        service_account_id: Union[UUID, str]
    ):
        """Delete an existing service account."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/service-accounts/{service_account_id}"
        self.client.request("delete", path)

    def regenerate_service_account_key(
        self,
        uid: Union[UUID, str],
        service_account_id: Union[UUID, str]
    ) -> Tuple["ServiceAccount", str]:
        """Regenerate an existing service account's key."""

        path = (
            f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}"
            f"/service-accounts/{service_account_id}/regenerate"
        )
        response = self.client.request("put", path).json()

        return self.get_service_account(uid, service_account_id), response["key"]

    def transfer_ownership(self, uid: Union[UUID, str], email: str) -> None:
        """Transfer ownership of a workspace to another HydroServer user."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/transfer"
        self.client.request("post", path, json={"newOwner": email})

    def accept_ownership_transfer(self, uid: Union[UUID, str]) -> None:
        """Accept ownership transfer of a workspace."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/transfer"
        self.client.request("put", path)

    def cancel_ownership_transfer(self, uid: Union[UUID, str]) -> None:
        """Cancel ownership transfer of a workspace."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/transfer"
        self.client.request("delete", path)
