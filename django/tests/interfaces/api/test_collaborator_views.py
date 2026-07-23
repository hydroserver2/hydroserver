import pytest

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)

pytestmark = pytest.mark.django_db


def _collaborators_url(workspace_id):
    return f"/api/data/workspaces/{workspace_id}/collaborators"


def _collaborator_with_permission(workspace, resource_type, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type=resource_type, **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


# --- get_collaborators ------------------------------------------------------


def test_get_collaborators_includes_collaborators_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    collaborator = CollaboratorFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_collaborators_url(workspace.id))

    assert response.status_code == 200
    emails = [c["user"]["email"] for c in response.json()]
    assert collaborator.user.email in emails


def test_get_collaborators_returns_404_for_workspace_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_collaborators_url(workspace.id))

    assert response.status_code == 404


# --- add_collaborator --------------------------------------------------------


def test_add_collaborator_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    role = RoleFactory(workspace=workspace)
    new_collaborator = UserFactory()
    client.force_login(owner)

    response = client.post(
        _collaborators_url(workspace.id),
        data={"email": new_collaborator.email, "roleId": str(role.id)},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["user"]["email"] == new_collaborator.email


def test_add_collaborator_returns_400_for_unknown_email(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    role = RoleFactory(workspace=workspace)
    client.force_login(owner)

    response = client.post(
        _collaborators_url(workspace.id),
        data={"email": "nobody@example.com", "roleId": str(role.id)},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_add_collaborator_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, "Workspace", can_view=True)
    role = RoleFactory(workspace=workspace)
    new_collaborator = UserFactory()
    client.force_login(collaborator.user)

    response = client.post(
        _collaborators_url(workspace.id),
        data={"email": new_collaborator.email, "roleId": str(role.id)},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- edit_collaborator_role ---------------------------------------------------


def test_edit_collaborator_role_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    collaborator = CollaboratorFactory(workspace=workspace)
    new_role = RoleFactory(workspace=workspace)
    client.force_login(owner)

    response = client.put(
        _collaborators_url(workspace.id),
        data={"email": collaborator.user.email, "roleId": str(new_role.id)},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["role"]["id"] == str(new_role.id)


def test_edit_collaborator_role_returns_400_for_unknown_collaborator(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    role = RoleFactory(workspace=workspace)
    client.force_login(owner)

    response = client.put(
        _collaborators_url(workspace.id),
        data={"email": "nobody@example.com", "roleId": str(role.id)},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_edit_collaborator_role_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    collaborator = CollaboratorFactory(workspace=workspace)
    outsider_collaborator = _collaborator_with_permission(
        workspace, "Collaborator", can_view=True
    )
    new_role = RoleFactory(workspace=workspace)
    client.force_login(outsider_collaborator.user)

    response = client.put(
        _collaborators_url(workspace.id),
        data={"email": collaborator.user.email, "roleId": str(new_role.id)},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- remove_collaborator ------------------------------------------------------


def test_remove_collaborator_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    collaborator = CollaboratorFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(
        _collaborators_url(workspace.id),
        data={"email": collaborator.user.email},
        content_type="application/json",
    )

    assert response.status_code == 204


def test_remove_collaborator_succeeds_for_self_removal(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, "Collaborator")  # no delete grant
    client.force_login(collaborator.user)

    response = client.delete(
        _collaborators_url(workspace.id),
        data={"email": collaborator.user.email},
        content_type="application/json",
    )

    assert response.status_code == 204


def test_remove_collaborator_returns_403_without_delete_permission_or_self(client):
    workspace = WorkspaceFactory()
    target = CollaboratorFactory(workspace=workspace)
    other_collaborator = _collaborator_with_permission(workspace, "Collaborator", can_view=True)
    client.force_login(other_collaborator.user)

    response = client.delete(
        _collaborators_url(workspace.id),
        data={"email": target.user.email},
        content_type="application/json",
    )

    assert response.status_code == 403
