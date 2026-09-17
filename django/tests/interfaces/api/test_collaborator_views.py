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

COLLABORATOR_FIELDS = {"roleId", "userEmail", "serviceAccountEmail"}


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
    emails = [c["userEmail"] for c in response.json()["data"]]
    assert collaborator.user.email in emails


def test_get_collaborators_paginates_in_stable_id_order(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    role = RoleFactory(workspace=workspace)
    first = CollaboratorFactory(
        workspace=workspace,
        role=role,
        service_account_collaborator=True,
    )
    second = CollaboratorFactory(
        workspace=workspace,
        role=role,
        service_account_collaborator=True,
    )
    collaborator = CollaboratorFactory(workspace=workspace, role=role)
    client.force_login(owner)

    first_page = client.get(
        f"{_collaborators_url(workspace.id)}?offset=0&limit=2"
    )
    second_page = client.get(
        f"{_collaborators_url(workspace.id)}?offset=2&limit=2"
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert [c["serviceAccountEmail"] for c in first_page.json()["data"]] == [
        first.service_account.email,
        second.service_account.email,
    ]
    assert second_page.json()["data"][0]["userEmail"] == collaborator.user.email


def test_get_collaborators_response_fields_are_flat_scalars(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    CollaboratorFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_collaborators_url(workspace.id))

    assert response.status_code == 200
    assert set(response.json()["data"][0].keys()) == COLLABORATOR_FIELDS


def test_get_collaborators_returns_404_for_workspace_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_collaborators_url(workspace.id))

    assert response.status_code == 404


def test_get_collaborators_include_role_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    role = RoleFactory(workspace=workspace)
    collaborator = CollaboratorFactory(workspace=workspace, role=role)
    client.force_login(owner)

    response = client.get(_collaborators_url(workspace.id), {"include": "role"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["roleId"] == str(collaborator.role_id)
    assert {row["id"] for row in body["included"]["roles"]} == {str(role.id)}


def test_get_collaborators_include_user_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    collaborator = CollaboratorFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_collaborators_url(workspace.id), {"include": "user"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["userEmail"] == collaborator.user.email
    assert {u["email"] for u in body["included"]["users"]} == {collaborator.user.email}


def test_get_collaborators_include_service_account_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    collaborator = CollaboratorFactory(
        workspace=workspace, service_account_collaborator=True
    )
    client.force_login(owner)

    response = client.get(
        _collaborators_url(workspace.id), {"include": "serviceAccount"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["serviceAccountEmail"] == collaborator.service_account.email
    assert {sa["email"] for sa in body["included"]["serviceAccounts"]} == {
        collaborator.service_account.email
    }


def test_get_collaborators_without_include_omits_included_bucket(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    CollaboratorFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_collaborators_url(workspace.id))

    assert response.status_code == 200
    assert not response.json().get("included")


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
    assert set(response.json().keys()) == {"id"}
    collaborators = client.get(_collaborators_url(workspace.id)).json()["data"]
    assert new_collaborator.email in [c["userEmail"] for c in collaborators]


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


def test_add_collaborator_succeeds_for_service_account_email(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    role = RoleFactory(workspace=workspace)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.post(
        _collaborators_url(workspace.id),
        data={"email": service_account.email, "roleId": str(role.id)},
        content_type="application/json",
    )

    assert response.status_code == 201
    collaborators = client.get(_collaborators_url(workspace.id)).json()["data"]
    added = next(c for c in collaborators if c["serviceAccountEmail"] == service_account.email)
    assert added["userEmail"] is None


def test_add_collaborator_succeeds_for_service_account_on_external_workspace(client):
    home_workspace = WorkspaceFactory()
    service_account = ServiceAccountFactory(workspace=home_workspace)
    external_owner = UserFactory()
    external_workspace = WorkspaceFactory(owner=external_owner)
    role = RoleFactory(workspace=external_workspace)
    client.force_login(external_owner)

    response = client.post(
        _collaborators_url(external_workspace.id),
        data={"email": service_account.email, "roleId": str(role.id)},
        content_type="application/json",
    )

    assert response.status_code == 201
    collaborators = client.get(_collaborators_url(external_workspace.id)).json()["data"]
    assert service_account.email in [c["serviceAccountEmail"] for c in collaborators]


def test_add_collaborator_returns_400_when_service_account_already_collaborates(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    role = RoleFactory(workspace=workspace)
    existing = CollaboratorFactory(
        workspace=workspace, service_account_collaborator=True, role=role
    )
    client.force_login(owner)

    response = client.post(
        _collaborators_url(workspace.id),
        data={"email": existing.service_account.email, "roleId": str(role.id)},
        content_type="application/json",
    )

    assert response.status_code == 400


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

    assert response.status_code == 204
    collaborator.refresh_from_db()
    assert collaborator.role_id == new_role.id


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


def test_edit_collaborator_role_succeeds_for_service_account(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    collaborator = CollaboratorFactory(
        workspace=workspace, service_account_collaborator=True
    )
    new_role = RoleFactory(workspace=workspace)
    client.force_login(owner)

    response = client.put(
        _collaborators_url(workspace.id),
        data={"email": collaborator.service_account.email, "roleId": str(new_role.id)},
        content_type="application/json",
    )

    assert response.status_code == 204
    collaborator.refresh_from_db()
    assert collaborator.role_id == new_role.id


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


def test_remove_collaborator_succeeds_for_service_account(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    collaborator = CollaboratorFactory(
        workspace=workspace, service_account_collaborator=True
    )
    client.force_login(owner)

    response = client.delete(
        _collaborators_url(workspace.id),
        data={"email": collaborator.service_account.email},
        content_type="application/json",
    )

    assert response.status_code == 204


def test_remove_collaborator_returns_403_for_service_account_without_delete_permission(client):
    workspace = WorkspaceFactory()
    target = CollaboratorFactory(workspace=workspace, service_account_collaborator=True)
    other_collaborator = _collaborator_with_permission(workspace, "Collaborator", can_view=True)
    client.force_login(other_collaborator.user)

    response = client.delete(
        _collaborators_url(workspace.id),
        data={"email": target.service_account.email},
        content_type="application/json",
    )

    assert response.status_code == 403
