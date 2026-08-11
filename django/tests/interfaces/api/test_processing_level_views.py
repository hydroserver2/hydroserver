import pytest

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, ProcessingLevelFactory

pytestmark = pytest.mark.django_db

PROCESSING_LEVELS_URL = "/api/data/processing-levels"


def _detail_url(processing_level_id):
    return f"{PROCESSING_LEVELS_URL}/{processing_level_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="ProcessingLevel", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _processing_level_body(**overrides):
    body = {
        "code": "0",
        "name": "Raw",
        "description": "A new processing level.",
    }
    body.update(overrides)
    return body


# --- get_processing_levels ---------------------------------------------------------


def test_get_processing_levels_includes_global_levels_for_anonymous(client):
    processing_level = ProcessingLevelFactory(global_=True)

    response = client.get(PROCESSING_LEVELS_URL)

    assert response.status_code == 200
    assert str(processing_level.id) in [p["id"] for p in response.json()]


def test_get_processing_levels_excludes_private_workspace_levels_for_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    ProcessingLevelFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(PROCESSING_LEVELS_URL)

    assert response.json() == []


def test_get_processing_levels_includes_workspace_levels_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    processing_level = ProcessingLevelFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(PROCESSING_LEVELS_URL)

    assert response.status_code == 200
    assert str(processing_level.id) in [p["id"] for p in response.json()]


# --- create_processing_level --------------------------------------------------------


def test_create_processing_level_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        PROCESSING_LEVELS_URL,
        data=_processing_level_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["code"] == "0"
    assert response.json()["name"] == "Raw"
    assert response.json()["description"] == "A new processing level."
    assert response.json()["definition"] is None


def test_create_processing_level_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        PROCESSING_LEVELS_URL,
        data=_processing_level_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_processing_level_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        PROCESSING_LEVELS_URL,
        data=_processing_level_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 403


# --- get_processing_level -----------------------------------------------------------


def test_get_processing_level_returns_global_level_for_anonymous(client):
    processing_level = ProcessingLevelFactory(global_=True)

    response = client.get(_detail_url(processing_level.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(processing_level.id)


def test_get_processing_level_returns_404_for_private_workspace_level_when_unrelated(
    client,
):
    workspace = WorkspaceFactory(is_private=True)
    processing_level = ProcessingLevelFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(processing_level.id))

    assert response.status_code == 404


def test_get_processing_level_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    processing_level = ProcessingLevelFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(processing_level.id))

    assert response.status_code == 200


def test_get_processing_level_returns_404_for_nonexistent_level(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- update_processing_level ---------------------------------------------------------


def test_update_processing_level_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    processing_level = ProcessingLevelFactory(workspace=workspace, code="Original Code")
    client.force_login(owner)

    response = client.patch(
        _detail_url(processing_level.id),
        data={"code": "Updated Code"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["code"] == "Updated Code"


def test_update_processing_level_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    processing_level = ProcessingLevelFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(processing_level.id),
        data={"code": "Updated Code"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_processing_level ---------------------------------------------------------


def test_delete_processing_level_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    processing_level = ProcessingLevelFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(processing_level.id))

    assert response.status_code == 204
    assert client.get(_detail_url(processing_level.id)).status_code == 404


def test_delete_processing_level_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    processing_level = ProcessingLevelFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(processing_level.id))

    assert response.status_code == 403


def test_delete_processing_level_returns_409_when_in_use_by_datastream(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    processing_level = ProcessingLevelFactory(workspace=workspace)
    DatastreamFactory(processing_level=processing_level)
    client.force_login(owner)

    response = client.delete(_detail_url(processing_level.id))

    assert response.status_code == 409
