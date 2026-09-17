import uuid
from unittest.mock import MagicMock

from hydroserverpy.api.models.iam.collaborator import Collaborator
from hydroserverpy.api.services.iam.workspace import WorkspaceService


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        if self._payload is None:
            raise ValueError("No JSON content (empty response body)")
        return self._payload


def make_client():
    client = MagicMock()
    client.base_route = "/api/data"
    return client


def test_collaborator_supports_service_account_principal():
    client = make_client()
    workspace_id = uuid.uuid4()
    role_id = uuid.uuid4()

    collaborator = Collaborator(
        client=client,
        uid=None,
        workspace_id=workspace_id,
        role_id=role_id,
        service_account_email="svc-account@example.com",
    )

    assert collaborator.is_service_account is True
    assert collaborator.email == "svc-account@example.com"

    collaborator.delete()

    client.workspaces.remove_collaborator.assert_called_once_with(
        uid=str(workspace_id), email="svc-account@example.com"
    )


def test_collaborator_supports_user_principal():
    client = make_client()
    collaborator = Collaborator(
        client=client,
        uid=None,
        workspace_id=uuid.uuid4(),
        role_id=uuid.uuid4(),
        user_email="person@example.com",
    )

    assert collaborator.is_service_account is False
    assert collaborator.email == "person@example.com"


def test_create_service_account_captures_key_and_refetches_canonical_state():
    client = make_client()
    workspace_id = uuid.uuid4()
    service_account_id = str(uuid.uuid4())

    client.request.side_effect = [
        FakeResponse({"id": service_account_id, "key": "hs_generated_key"}, status_code=201),
        FakeResponse(
            {
                "data": {
                    "id": service_account_id,
                    "name": "My Service Account",
                    "email": "svc@example.com",
                    "workspaceId": str(workspace_id),
                    "isActive": True,
                    "createdAt": "2026-01-01T00:00:00Z",
                }
            }
        ),
    ]

    service = WorkspaceService(client)
    service_account, key = service.create_service_account(
        uid=workspace_id, name="My Service Account"
    )

    assert key == "hs_generated_key"
    assert str(service_account.uid) == service_account_id
    assert service_account.name == "My Service Account"
    assert client.request.call_count == 2
