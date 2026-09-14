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
    assert str(processing_level.id) in [p["id"] for p in response.json()["data"]]


def test_get_processing_levels_excludes_private_workspace_levels_for_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    ProcessingLevelFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(PROCESSING_LEVELS_URL)

    assert response.json()["data"] == []


def test_get_processing_levels_includes_workspace_levels_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    processing_level = ProcessingLevelFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(PROCESSING_LEVELS_URL)

    assert response.status_code == 200
    assert str(processing_level.id) in [p["id"] for p in response.json()["data"]]


def test_get_processing_levels_properties_filters_every_item_in_the_list(client):
    ProcessingLevelFactory(global_=True, code="0", name="Raw")
    ProcessingLevelFactory(global_=True, code="1", name="QC-1")

    response = client.get(PROCESSING_LEVELS_URL, {"properties": "id,code"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "code"}


def test_get_processing_levels_properties_accepts_repeated_key_style_too(client):
    ProcessingLevelFactory(global_=True, code="0")

    response = client.get(PROCESSING_LEVELS_URL, {"properties": ["id", "code"]})

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "code"}


def test_get_processing_levels_properties_rejects_unknown_property(client):
    response = client.get(PROCESSING_LEVELS_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_processing_levels_without_properties_returns_every_field(client):
    ProcessingLevelFactory(global_=True, code="0", name="Raw")

    response = client.get(PROCESSING_LEVELS_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {
        "id",
        "code",
        "name",
        "description",
        "definition",
        "workspaceId",
    }


def test_get_processing_levels_has_no_included_key_without_include_param(client):
    ProcessingLevelFactory(global_=True)

    response = client.get(PROCESSING_LEVELS_URL)

    assert response.status_code == 200
    assert "included" not in response.json()


def test_get_processing_levels_include_workspace_deduplicates_across_items(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ProcessingLevelFactory(workspace=workspace, code="0")
    ProcessingLevelFactory(workspace=workspace, code="1")
    client.force_login(owner)

    response = client.get(PROCESSING_LEVELS_URL, {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_processing_levels_include_rejects_unknown_relation(client):
    response = client.get(PROCESSING_LEVELS_URL, {"include": "bogus"})

    assert response.status_code == 400


def test_get_processing_levels_properties_does_not_filter_included_resources(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner, name="Acme")
    ProcessingLevelFactory(workspace=workspace, code="0")
    client.force_login(owner)

    response = client.get(
        PROCESSING_LEVELS_URL, {"properties": "code", "include": "workspace"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0] == {"code": "0"}
    included_workspace = body["included"]["workspaces"][0]
    assert included_workspace["id"] == str(workspace.id)
    assert included_workspace["name"] == "Acme"


def test_get_processing_levels_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ProcessingLevelFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(PROCESSING_LEVELS_URL, {"include": ["workspace"]})

    assert response.status_code == 200
    body = response.json()
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_processing_levels_include_workspace_does_not_scale_queries_with_count(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    for _ in range(5):
        ProcessingLevelFactory(workspace=workspace)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(PROCESSING_LEVELS_URL, {"include": "workspace"})

    for _ in range(5):
        ProcessingLevelFactory(workspace=workspace)

    with CaptureQueriesContext(connection) as large:
        client.get(PROCESSING_LEVELS_URL, {"include": "workspace"})

    assert len(large.captured_queries) == len(small.captured_queries)


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
    assert set(response.json().keys()) == {"id"}
    processing_level_id = response.json()["id"]

    detail = client.get(_detail_url(processing_level_id))
    assert detail.json()["data"]["code"] == "0"
    assert detail.json()["data"]["name"] == "Raw"
    assert detail.json()["data"]["description"] == "A new processing level."
    assert detail.json()["data"]["definition"] is None


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
    assert response.json()["data"]["id"] == str(processing_level.id)


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


def test_get_processing_level_included_is_present_but_empty_without_include_param(
    client,
):
    processing_level = ProcessingLevelFactory(global_=True)

    response = client.get(_detail_url(processing_level.id))

    assert response.status_code == 200
    body = response.json()
    assert "included" in body
    assert body["included"] == {}


def test_get_processing_level_include_workspace_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    processing_level = ProcessingLevelFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(processing_level.id), {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(processing_level.id)
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_processing_level_include_rejects_unknown_relation(client):
    processing_level = ProcessingLevelFactory(global_=True)

    response = client.get(_detail_url(processing_level.id), {"include": "bogus"})

    assert response.status_code == 400


def test_get_processing_level_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    processing_level = ProcessingLevelFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(processing_level.id), {"include": ["workspace"]})

    assert response.status_code == 200
    body = response.json()
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_processing_level_properties_rejects_unknown_property(client):
    processing_level = ProcessingLevelFactory(global_=True)

    response = client.get(_detail_url(processing_level.id), {"properties": "bogus"})

    assert response.status_code == 400


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

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(processing_level.id))
    assert detail.json()["data"]["code"] == "Updated Code"


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
