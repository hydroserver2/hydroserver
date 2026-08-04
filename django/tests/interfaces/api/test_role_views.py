import pytest

from tests.core.iam.factories import RoleFactory, UserFactory, WorkspaceFactory

pytestmark = pytest.mark.django_db

ROLES_URL = "/api/data/roles"


def _detail_url(role_id):
    return f"{ROLES_URL}/{role_id}"


# --- get_roles ----------------------------------------------------------------


def test_get_roles_includes_global_roles_for_anonymous(client):
    role = RoleFactory(global_role=True)

    response = client.get(ROLES_URL)

    assert response.status_code == 200
    assert str(role.id) in [r["id"] for r in response.json()]


def test_get_roles_excludes_workspace_roles_for_unrelated_user(client):
    RoleFactory()  # workspace-scoped, belongs to some other workspace/owner
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(ROLES_URL)

    assert response.json() == []


def test_get_roles_includes_workspace_roles_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    role = RoleFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(ROLES_URL)

    assert response.status_code == 200
    assert str(role.id) in [r["id"] for r in response.json()]


# --- get_role ------------------------------------------------------------------


def test_get_role_returns_global_role_for_anonymous(client):
    role = RoleFactory(global_role=True)

    response = client.get(_detail_url(role.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(role.id)


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
