import pytest

from core.sta.models import UnitType
from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, UnitFactory

pytestmark = pytest.mark.django_db

UNITS_URL = "/api/data/units"


def _detail_url(unit_id):
    return f"{UNITS_URL}/{unit_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Unit", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _unit_body(**overrides):
    body = {
        "name": "New Unit",
        "symbol": "u",
        "definition": "https://example.com/units/u",
        "type": "Dimensionless",
    }
    body.update(overrides)
    return body


# --- get_units ------------------------------------------------------------------


def test_get_units_includes_global_units_for_anonymous(client):
    unit = UnitFactory(global_=True)

    response = client.get(UNITS_URL)

    assert response.status_code == 200
    assert str(unit.id) in [u["id"] for u in response.json()]


def test_get_units_excludes_private_workspace_units_for_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    UnitFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(UNITS_URL)

    assert response.json() == []


def test_get_units_includes_workspace_units_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    unit = UnitFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(UNITS_URL)

    assert response.status_code == 200
    assert str(unit.id) in [u["id"] for u in response.json()]


def test_get_units_filters_by_type(client):
    length = UnitFactory(global_=True, type="Length")
    UnitFactory(global_=True, type="Temperature")

    response = client.get(UNITS_URL, {"type": "Length"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(length.id)]


# --- create_unit ------------------------------------------------------------------


def test_create_unit_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        UNITS_URL,
        data=_unit_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["name"] == "New Unit"
    assert response.json()["type"] == "Dimensionless"


def test_create_unit_allows_omitting_definition(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)
    body = _unit_body(workspaceId=str(workspace.id))
    body.pop("definition")

    response = client.post(
        UNITS_URL,
        data=body,
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["definition"] is None


def test_create_unit_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        UNITS_URL,
        data=_unit_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_unit_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        UNITS_URL,
        data=_unit_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 403


# --- get_unit_types ----------------------------------------------------------------


def test_get_unit_types_returns_registered_type_names(client):
    UnitType.objects.create(name="Dimensionless")
    UnitType.objects.create(name="Length")

    response = client.get(f"{UNITS_URL}/types")

    assert response.status_code == 200
    assert set(response.json()) == {"Dimensionless", "Length"}


# --- get_unit --------------------------------------------------------------------


def test_get_unit_returns_global_unit_for_anonymous(client):
    unit = UnitFactory(global_=True)

    response = client.get(_detail_url(unit.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(unit.id)


def test_get_unit_returns_404_for_private_workspace_unit_when_unrelated(client):
    workspace = WorkspaceFactory(is_private=True)
    unit = UnitFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(unit.id))

    assert response.status_code == 404


def test_get_unit_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    unit = UnitFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(unit.id))

    assert response.status_code == 200


def test_get_unit_returns_404_for_nonexistent_unit(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- update_unit ------------------------------------------------------------------


def test_update_unit_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    unit = UnitFactory(workspace=workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(unit.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_update_unit_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    unit = UnitFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(unit.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_unit ------------------------------------------------------------------


def test_delete_unit_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    unit = UnitFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(unit.id))

    assert response.status_code == 204
    assert client.get(_detail_url(unit.id)).status_code == 404


def test_delete_unit_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    unit = UnitFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(unit.id))

    assert response.status_code == 403


def test_delete_unit_returns_409_when_in_use_by_datastream(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    unit = UnitFactory(workspace=workspace)
    DatastreamFactory(unit=unit)
    client.force_login(owner)

    response = client.delete(_detail_url(unit.id))

    assert response.status_code == 409
