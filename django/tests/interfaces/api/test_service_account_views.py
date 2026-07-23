import pytest

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    ServiceAccountFactory,
    UserFactory,
    WorkspaceFactory,
)

pytestmark = pytest.mark.django_db


def _service_accounts_url(workspace_id):
    return f"/api/data/workspaces/{workspace_id}/service-accounts"


def _detail_url(workspace_id, service_account_id):
    return f"{_service_accounts_url(workspace_id)}/{service_account_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="ServiceAccount", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


# --- get_service_accounts ----------------------------------------------------


def test_get_service_accounts_includes_accounts_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_service_accounts_url(workspace.id))

    assert response.status_code == 200
    assert str(service_account.id) in [sa["id"] for sa in response.json()]


def test_get_service_accounts_returns_404_for_workspace_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_service_accounts_url(workspace.id))

    assert response.status_code == 404


# --- create_service_account ---------------------------------------------------


def test_create_service_account_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        _service_accounts_url(workspace.id),
        data={"name": "New Service Account", "isActive": True},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["key"]


def test_create_service_account_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        _service_accounts_url(workspace.id),
        data={"name": "New Service Account", "isActive": True},
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_service_account_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        _service_accounts_url(workspace.id),
        data={"name": "New Service Account", "isActive": True},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- get_service_account --------------------------------------------------------


def test_get_service_account_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(workspace.id, service_account.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(service_account.id)


def test_get_service_account_returns_404_for_workspace_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    service_account = ServiceAccountFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(workspace.id, service_account.id))

    assert response.status_code == 404


def test_get_service_account_returns_404_for_nonexistent_account(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(
        _detail_url(workspace.id, "00000000-0000-0000-0000-000000000000")
    )

    assert response.status_code == 404


# --- update_service_account ---------------------------------------------------


def test_update_service_account_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(workspace.id, service_account.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_update_service_account_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    service_account = ServiceAccountFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(workspace.id, service_account.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_service_account ---------------------------------------------------


def test_delete_service_account_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(workspace.id, service_account.id))

    assert response.status_code == 204
    assert client.get(_detail_url(workspace.id, service_account.id)).status_code == 404


def test_delete_service_account_returns_403_without_delete_permission(client):
    workspace = WorkspaceFactory()
    service_account = ServiceAccountFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(workspace.id, service_account.id))

    assert response.status_code == 403


# --- regenerate_service_account_key --------------------------------------------


def test_regenerate_service_account_key_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.put(f"{_detail_url(workspace.id, service_account.id)}/regenerate")

    assert response.status_code == 201
    assert response.json()["key"]


def test_regenerate_service_account_key_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    service_account = ServiceAccountFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.put(f"{_detail_url(workspace.id, service_account.id)}/regenerate")

    assert response.status_code == 403
