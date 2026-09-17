import pytest

from django.test.utils import CaptureQueriesContext
from django.db import connection

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
    assert str(unit.id) in [u["id"] for u in response.json()["data"]]


def test_get_units_excludes_private_workspace_units_for_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    UnitFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(UNITS_URL)

    assert response.json()["data"] == []


def test_get_units_includes_workspace_units_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    unit = UnitFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(UNITS_URL)

    assert response.status_code == 200
    assert str(unit.id) in [u["id"] for u in response.json()["data"]]


def test_get_units_filters_by_type(client):
    length = UnitFactory(global_=True, type="Length")
    UnitFactory(global_=True, type="Temperature")

    response = client.get(UNITS_URL, {"type": "Length"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(length.id)]


def test_get_units_properties_filters_every_item_in_the_list(client):
    UnitFactory(global_=True, name="Meter", symbol="m")
    UnitFactory(global_=True, name="Liter", symbol="L")

    response = client.get(UNITS_URL, {"properties": "id,name"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "name"}


def test_get_units_properties_accepts_repeated_key_style_too(client):
    UnitFactory(global_=True, name="Meter", symbol="m")

    response = client.get(UNITS_URL, {"properties": ["id", "name"]})

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name"}


def test_get_units_properties_rejects_unknown_property(client):
    response = client.get(UNITS_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_units_without_properties_returns_every_field(client):
    UnitFactory(global_=True, name="Meter", symbol="m", type="Length")

    response = client.get(UNITS_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name", "symbol", "definition", "type", "workspaceId"}


def test_get_units_has_no_included_key_without_include_param(client):
    UnitFactory(global_=True)

    response = client.get(UNITS_URL)

    assert response.status_code == 200
    assert "included" not in response.json()


def test_get_units_include_workspace_deduplicates_across_items(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    UnitFactory(workspace=workspace, name="Meter")
    UnitFactory(workspace=workspace, name="Liter")
    client.force_login(owner)

    response = client.get(UNITS_URL, {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_units_include_workspace_skips_global_units_without_error(client):
    UnitFactory(global_=True)

    response = client.get(UNITS_URL, {"include": "workspace"})

    assert response.status_code == 200
    assert "included" not in response.json()


def test_get_units_include_rejects_unknown_relation(client):
    response = client.get(UNITS_URL, {"include": "bogus"})

    assert response.status_code == 400


def test_get_units_properties_and_include_together(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    UnitFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(
        UNITS_URL, {"properties": "id,name", "include": "workspace"}
    )

    assert response.status_code == 200
    body = response.json()
    for item in body["data"]:
        assert set(item.keys()) == {"id", "name"}
    assert body["included"]["workspaces"][0]["id"] == str(workspace.id)


def test_get_units_properties_does_not_filter_included_resources(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner, name="Acme")
    UnitFactory(workspace=workspace, symbol="m")
    client.force_login(owner)

    response = client.get(
        UNITS_URL, {"properties": "symbol", "include": "workspace"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0] == {"symbol": "m"}
    included_workspace = body["included"]["workspaces"][0]
    assert included_workspace["id"] == str(workspace.id)
    assert included_workspace["name"] == "Acme"


def test_get_units_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    UnitFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(UNITS_URL, {"include": ["workspace"]})

    assert response.status_code == 200
    body = response.json()
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_units_include_workspace_does_not_scale_queries_with_unit_count(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    for _ in range(5):
        UnitFactory(workspace=workspace)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(UNITS_URL, {"include": "workspace"})

    UnitFactory(workspace=workspace)
    UnitFactory(workspace=workspace)
    UnitFactory(workspace=workspace)
    UnitFactory(workspace=workspace)
    UnitFactory(workspace=workspace)

    with CaptureQueriesContext(connection) as large:
        client.get(UNITS_URL, {"include": "workspace"})

    assert len(large.captured_queries) == len(small.captured_queries)


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
    assert set(response.json().keys()) == {"id"}


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
    unit_id = response.json()["id"]

    detail = client.get(_detail_url(unit_id), {"properties": "definition"})
    assert detail.json()["data"]["definition"] is None


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
    assert set(response.json()["data"]) == {"Dimensionless", "Length"}


# --- get_unit --------------------------------------------------------------------


def test_get_unit_returns_global_unit_for_anonymous(client):
    unit = UnitFactory(global_=True)

    response = client.get(_detail_url(unit.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(unit.id)


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


def test_get_unit_included_is_present_but_empty_without_include_param(client):
    unit = UnitFactory(global_=True)

    response = client.get(_detail_url(unit.id))

    assert response.status_code == 200
    body = response.json()
    assert "included" in body
    assert body["included"] == {}


def test_get_unit_include_workspace_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    unit = UnitFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(unit.id), {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(unit.id)
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_unit_include_rejects_unknown_relation(client):
    unit = UnitFactory(global_=True)

    response = client.get(_detail_url(unit.id), {"include": "bogus"})

    assert response.status_code == 400


def test_get_unit_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    unit = UnitFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(unit.id), {"include": ["workspace"]})

    assert response.status_code == 200
    body = response.json()
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_unit_properties_rejects_unknown_property(client):
    unit = UnitFactory(global_=True)

    response = client.get(_detail_url(unit.id), {"properties": "bogus"})

    assert response.status_code == 400


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

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(unit.id))
    assert detail.json()["data"]["name"] == "Updated Name"


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
