import pytest

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)

pytestmark = pytest.mark.django_db

WORKSPACES_URL = "/api/data/workspaces"


def _detail_url(workspace_id):
    return f"{WORKSPACES_URL}/{workspace_id}"


def _transfer_url(workspace_id):
    return f"{WORKSPACES_URL}/{workspace_id}/transfer"


def _viewer_collaborator(workspace):
    """A collaborator who can view this workspace but not edit or delete it."""

    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Workspace", can_view=True)
    return CollaboratorFactory(workspace=workspace, role=role)


# --- get_workspace --------------------------------------------------------------


def test_get_workspace_returns_workspace_for_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(_detail_url(workspace.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(workspace.id)


def test_get_workspace_returns_404_for_user_without_access(client):
    workspace = WorkspaceFactory(is_private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(workspace.id))

    assert response.status_code == 404


def test_get_workspace_returns_404_for_nonexistent_workspace(client):
    user = UserFactory()
    client.force_login(user)

    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- create_workspace ------------------------------------------------------------


def test_create_workspace_succeeds_for_authenticated_user(client):
    user = UserFactory()
    client.force_login(user)

    response = client.post(
        WORKSPACES_URL,
        data={"name": "New Workspace", "isPrivate": False},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["name"] == "New Workspace"


def test_create_workspace_returns_401_when_unauthenticated(client):
    response = client.post(
        WORKSPACES_URL,
        data={"name": "New Workspace", "isPrivate": False},
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_workspace_returns_422_when_owner_at_workspace_limit(client):
    owner = UserFactory(owned_workspace_limit=1)
    WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        WORKSPACES_URL,
        data={"name": "Second Workspace", "isPrivate": False},
        content_type="application/json",
    )

    assert response.status_code == 422


# --- get_workspaces ---------------------------------------------------------------


def test_get_workspaces_includes_workspaces_owned_by_the_user(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(WORKSPACES_URL)

    assert response.status_code == 200
    assert str(workspace.id) in [w["id"] for w in response.json()]


def test_get_workspaces_excludes_private_workspaces_of_others(client):
    WorkspaceFactory(is_private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(WORKSPACES_URL)

    assert response.status_code == 200
    assert response.json() == []


# --- update_workspace ---------------------------------------------------------------


def test_update_workspace_succeeds_for_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(workspace.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_update_workspace_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    collaborator = _viewer_collaborator(workspace)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(workspace.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_update_workspace_returns_422_for_blank_name(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.patch(
        _detail_url(workspace.id),
        data={"name": ""},
        content_type="application/json",
    )

    assert response.status_code == 422


# --- delete_workspace ---------------------------------------------------------------


def test_delete_workspace_succeeds_for_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.delete(_detail_url(workspace.id))

    assert response.status_code == 204
    assert client.get(_detail_url(workspace.id)).status_code == 404


def test_delete_workspace_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    collaborator = _viewer_collaborator(workspace)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(workspace.id))

    assert response.status_code == 403


# --- transfer_workspace ---------------------------------------------------------------


def test_transfer_workspace_succeeds_for_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    new_owner = UserFactory()
    client.force_login(owner)

    response = client.post(
        _transfer_url(workspace.id),
        data={"newOwner": new_owner.email},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert workspace.transfer_confirmation.new_owner == new_owner


def test_transfer_workspace_returns_400_when_transferring_to_self(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        _transfer_url(workspace.id),
        data={"newOwner": owner.email},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_transfer_workspace_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    collaborator = _viewer_collaborator(workspace)
    new_owner = UserFactory()
    client.force_login(collaborator.user)

    response = client.post(
        _transfer_url(workspace.id),
        data={"newOwner": new_owner.email},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- accept_workspace_transfer ---------------------------------------------------------


def test_accept_workspace_transfer_succeeds_for_new_owner(client):
    owner = UserFactory()
    new_owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    workspace.initiate_transfer(new_owner)
    client.force_login(new_owner)

    response = client.put(_transfer_url(workspace.id))

    assert response.status_code == 200
    workspace.refresh_from_db()
    assert workspace.owner == new_owner


def test_accept_workspace_transfer_returns_400_when_nothing_pending(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.put(_transfer_url(workspace.id))

    assert response.status_code == 400


# --- reject_workspace_transfer ---------------------------------------------------------


def test_reject_workspace_transfer_succeeds_for_owner(client):
    owner = UserFactory()
    new_owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    workspace.initiate_transfer(new_owner)
    client.force_login(owner)

    response = client.delete(_transfer_url(workspace.id))

    assert response.status_code == 200
    workspace.refresh_from_db()
    assert workspace.owner == owner
    assert workspace.transfer is None


def test_reject_workspace_transfer_returns_400_when_nothing_pending(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.delete(_transfer_url(workspace.id))

    assert response.status_code == 400
