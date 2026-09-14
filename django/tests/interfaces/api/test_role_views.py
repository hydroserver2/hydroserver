import pytest

from tests.core.iam.factories import (
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)

pytestmark = pytest.mark.django_db

ROLES_URL = "/api/data/roles"


def _detail_url(role_id):
    return f"{ROLES_URL}/{role_id}"


# --- get_roles ----------------------------------------------------------------


def test_get_roles_includes_global_roles_for_anonymous(client):
    role = RoleFactory(global_role=True)

    response = client.get(ROLES_URL)

    assert response.status_code == 200
    assert str(role.id) in [r["id"] for r in response.json()["data"]]


def test_get_roles_excludes_workspace_roles_for_unrelated_user(client):
    RoleFactory()  # workspace-scoped, belongs to some other workspace/owner
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(ROLES_URL)

    assert response.json()["data"] == []


def test_get_roles_includes_workspace_roles_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    role = RoleFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(ROLES_URL)

    assert response.status_code == 200
    assert str(role.id) in [r["id"] for r in response.json()["data"]]


# --- get_role ------------------------------------------------------------------


def test_get_role_returns_global_role_for_anonymous(client):
    role = RoleFactory(global_role=True)

    response = client.get(_detail_url(role.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(role.id)


def test_get_role_returns_404_for_workspace_role_when_unrelated(client):
    role = RoleFactory()  # workspace-scoped
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(role.id))

    assert response.status_code == 404


def test_get_role_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    role = RoleFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(role.id))

    assert response.status_code == 200


def test_get_role_returns_404_for_nonexistent_role(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- permissions expansion / properties ----------------------------------------


def test_get_role_expands_permission_flags_into_resource_action_pairs(client):
    role = RoleFactory(global_role=True)
    PermissionFactory(role=role, resource_type="Workspace", can_view=True, can_edit=True)

    response = client.get(_detail_url(role.id))

    assert response.status_code == 200
    permissions = response.json()["data"]["permissions"]
    pairs = {(p["resource"], p["action"]) for p in permissions}
    assert ("Workspace", "view") in pairs
    assert ("Workspace", "edit") in pairs
    assert ("Workspace", "create") not in pairs
    assert ("Workspace", "delete") not in pairs


def test_get_roles_permissions_survive_the_response_wrappers_double_validation(client):
    role_a = RoleFactory(global_role=True, name="Role A")
    role_b = RoleFactory(global_role=True, name="Role B")
    PermissionFactory(role=role_a, resource_type="Workspace", can_view=True)
    PermissionFactory(role=role_b, resource_type="Datastream", can_edit=True)

    response = client.get(ROLES_URL)

    assert response.status_code == 200
    by_id = {r["id"]: r for r in response.json()["data"]}
    assert {"resource": "Workspace", "action": "view"} in by_id[str(role_a.id)]["permissions"]
    assert {"resource": "Datastream", "action": "edit"} in by_id[str(role_b.id)]["permissions"]


def test_get_roles_properties_filters_response_fields(client):
    RoleFactory(global_role=True)

    response = client.get(ROLES_URL, {"properties": "id,name"})

    assert response.status_code == 200
    row = response.json()["data"][0]
    assert set(row.keys()) == {"id", "name"}
