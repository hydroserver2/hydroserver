import pytest

from django.test.utils import CaptureQueriesContext
from django.db import connection

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, MethodFactory

pytestmark = pytest.mark.django_db

METHODS_URL = "/api/data/methods"


def _detail_url(method_id):
    return f"{METHODS_URL}/{method_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Method", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _method_body(**overrides):
    body = {
        "name": "New Method",
        "code": "METHOD-1",
        "type": "Instrument Deployment",
        "description": "A new method.",
        "definition": "https://example.com/methods/1",
        "sensorModel": "Model A",
        "sensorModelManufacturer": "Manufacturer A",
        "sensorModelDefinition": "https://example.com/models/a",
    }
    body.update(overrides)
    return body


# --- get_methods ------------------------------------------------------------------


def test_get_methods_includes_global_methods_for_anonymous(client):
    method = MethodFactory(global_=True)

    response = client.get(METHODS_URL)

    assert response.status_code == 200
    assert str(method.id) in [s["id"] for s in response.json()["data"]]


def test_get_methods_excludes_private_workspace_methods_for_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    MethodFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(METHODS_URL)

    assert response.json()["data"] == []


def test_get_methods_includes_workspace_methods_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    method = MethodFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(METHODS_URL)

    assert response.status_code == 200
    assert str(method.id) in [s["id"] for s in response.json()["data"]]


def test_get_methods_properties_filters_every_item_in_the_list(client):
    MethodFactory(global_=True, name="Sensor A")
    MethodFactory(global_=True, name="Sensor B")

    response = client.get(METHODS_URL, {"properties": "id,name"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "name"}


def test_get_methods_properties_accepts_repeated_key_style_too(client):
    MethodFactory(global_=True, name="Sensor A")

    response = client.get(METHODS_URL, {"properties": ["id", "name"]})

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name"}


def test_get_methods_properties_rejects_unknown_property(client):
    response = client.get(METHODS_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_methods_without_properties_returns_every_field(client):
    MethodFactory(global_=True, name="Sensor A", type="Instrument Deployment")

    response = client.get(METHODS_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {
        "id",
        "name",
        "code",
        "type",
        "description",
        "definition",
        "sensorModel",
        "sensorModelManufacturer",
        "sensorModelDefinition",
        "workspaceId",
    }


def test_get_methods_has_no_included_key_without_include_param(client):
    MethodFactory(global_=True)

    response = client.get(METHODS_URL)

    assert response.status_code == 200
    assert "included" not in response.json()


def test_get_methods_include_workspace_deduplicates_across_items(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    MethodFactory(workspace=workspace, name="Sensor A")
    MethodFactory(workspace=workspace, name="Sensor B")
    client.force_login(owner)

    response = client.get(METHODS_URL, {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_methods_include_rejects_unknown_relation(client):
    response = client.get(METHODS_URL, {"include": "bogus"})

    assert response.status_code == 400


def test_get_methods_properties_does_not_filter_included_resources(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner, name="Acme")
    MethodFactory(workspace=workspace, code="METHOD-1")
    client.force_login(owner)

    response = client.get(METHODS_URL, {"properties": "code", "include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0] == {"code": "METHOD-1"}
    included_workspace = body["included"]["workspaces"][0]
    assert included_workspace["id"] == str(workspace.id)
    assert included_workspace["name"] == "Acme"


def test_get_methods_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    MethodFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(METHODS_URL, {"include": ["workspace"]})

    assert response.status_code == 200
    body = response.json()
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_methods_include_workspace_does_not_scale_queries_with_count(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    for _ in range(5):
        MethodFactory(workspace=workspace)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(METHODS_URL, {"include": "workspace"})

    for _ in range(5):
        MethodFactory(workspace=workspace)

    with CaptureQueriesContext(connection) as large:
        client.get(METHODS_URL, {"include": "workspace"})

    assert len(large.captured_queries) == len(small.captured_queries)


# --- create_method ------------------------------------------------------------------


def test_create_method_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        METHODS_URL,
        data=_method_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}


def test_create_method_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        METHODS_URL,
        data=_method_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_method_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        METHODS_URL,
        data=_method_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 403


# --- get_method --------------------------------------------------------------------


def test_get_method_returns_global_method_for_anonymous(client):
    method = MethodFactory(global_=True)

    response = client.get(_detail_url(method.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(method.id)


def test_get_method_returns_404_for_private_workspace_method_when_unrelated(client):
    workspace = WorkspaceFactory(is_private=True)
    method = MethodFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(method.id))

    assert response.status_code == 404


def test_get_method_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    method = MethodFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(method.id))

    assert response.status_code == 200


def test_get_method_returns_404_for_nonexistent_method(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_method_included_is_present_but_empty_without_include_param(client):
    method = MethodFactory(global_=True)

    response = client.get(_detail_url(method.id))

    assert response.status_code == 200
    body = response.json()
    assert "included" in body
    assert body["included"] == {}


def test_get_method_include_workspace_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    method = MethodFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(method.id), {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(method.id)
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_method_include_rejects_unknown_relation(client):
    method = MethodFactory(global_=True)

    response = client.get(_detail_url(method.id), {"include": "bogus"})

    assert response.status_code == 400


def test_get_method_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    method = MethodFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(method.id), {"include": ["workspace"]})

    assert response.status_code == 200
    body = response.json()
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_method_properties_rejects_unknown_property(client):
    method = MethodFactory(global_=True)

    response = client.get(_detail_url(method.id), {"properties": "bogus"})

    assert response.status_code == 400


# --- update_method ------------------------------------------------------------------


def test_update_method_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    method = MethodFactory(workspace=workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(method.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(method.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_method_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    method = MethodFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(method.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_method ------------------------------------------------------------------


def test_delete_method_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    method = MethodFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(method.id))

    assert response.status_code == 204
    assert client.get(_detail_url(method.id)).status_code == 404


def test_delete_method_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    method = MethodFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(method.id))

    assert response.status_code == 403


def test_delete_method_returns_409_when_in_use_by_datastream(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    method = MethodFactory(workspace=workspace)
    DatastreamFactory(method=method)
    client.force_login(owner)

    response = client.delete(_detail_url(method.id))

    assert response.status_code == 409
