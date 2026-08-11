import pytest

from core.sta.models import MethodType
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
    assert str(method.id) in [s["id"] for s in response.json()]


def test_get_methods_excludes_private_workspace_methods_for_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    MethodFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(METHODS_URL)

    assert response.json() == []


def test_get_methods_includes_workspace_methods_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    method = MethodFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(METHODS_URL)

    assert response.status_code == 200
    assert str(method.id) in [s["id"] for s in response.json()]


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
    assert response.json()["name"] == "New Method"
    assert response.json()["code"] == "METHOD-1"
    assert response.json()["type"] == "Instrument Deployment"
    assert response.json()["definition"] == "https://example.com/methods/1"
    assert response.json()["sensorModel"] == "Model A"
    assert response.json()["sensorModelManufacturer"] == "Manufacturer A"
    assert response.json()["sensorModelDefinition"] == "https://example.com/models/a"


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


def test_get_method_types_returns_registered_type_names(client):
    MethodType.objects.create(name="Instrument Deployment")
    MethodType.objects.create(name="Estimation")

    response = client.get(f"{METHODS_URL}/types")

    assert response.status_code == 200
    assert set(response.json()) == {"Instrument Deployment", "Estimation"}


# --- get_method --------------------------------------------------------------------


def test_get_method_returns_global_method_for_anonymous(client):
    method = MethodFactory(global_=True)

    response = client.get(_detail_url(method.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(method.id)


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

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


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
