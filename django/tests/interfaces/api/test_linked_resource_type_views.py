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
from tests.core.sta.factories import LinkedResourceTypeFactory

pytestmark = pytest.mark.django_db

LINKED_RESOURCE_TYPES_URL = "/api/data/linked-resource-types"


def _detail_url(linked_resource_type_id):
    return f"{LINKED_RESOURCE_TYPES_URL}/{linked_resource_type_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="LinkedResourceType", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _linked_resource_type_body(**overrides):
    body = {
        "name": "New Term",
        "description": "A new linked resource type.",
    }
    body.update(overrides)
    return body


# --- get_linked_resource_types -------------------------------------------------------


def test_get_linked_resource_types_includes_global_terms_for_anonymous(client):
    linked_resource_type = LinkedResourceTypeFactory(global_=True)

    response = client.get(LINKED_RESOURCE_TYPES_URL)

    assert response.status_code == 200
    assert str(linked_resource_type.id) in [r["id"] for r in response.json()["data"]]


def test_get_linked_resource_types_excludes_private_workspace_terms_for_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    LinkedResourceTypeFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(LINKED_RESOURCE_TYPES_URL)

    assert response.json()["data"] == []


def test_get_linked_resource_types_includes_workspace_terms_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    linked_resource_type = LinkedResourceTypeFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(LINKED_RESOURCE_TYPES_URL)

    assert response.status_code == 200
    assert str(linked_resource_type.id) in [r["id"] for r in response.json()["data"]]


def test_get_linked_resource_types_without_properties_returns_every_field(client):
    LinkedResourceTypeFactory(global_=True, name="A")

    response = client.get(LINKED_RESOURCE_TYPES_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name", "description", "isActive", "workspaceId"}


def test_get_linked_resource_types_has_no_included_key_without_include_param(client):
    LinkedResourceTypeFactory(global_=True)

    response = client.get(LINKED_RESOURCE_TYPES_URL)

    assert response.status_code == 200
    assert "included" not in response.json()


def test_get_linked_resource_types_include_workspace_deduplicates_across_items(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    LinkedResourceTypeFactory(workspace=workspace, name="A")
    LinkedResourceTypeFactory(workspace=workspace, name="B")
    client.force_login(owner)

    response = client.get(LINKED_RESOURCE_TYPES_URL, {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_linked_resource_types_include_rejects_unknown_relation(client):
    response = client.get(LINKED_RESOURCE_TYPES_URL, {"include": "bogus"})

    assert response.status_code == 400


def test_get_linked_resource_types_q_searches_name_and_description(client):
    LinkedResourceTypeFactory(global_=True, name="Average", description="")
    LinkedResourceTypeFactory(global_=True, name="Maximum", description="")

    response = client.get(LINKED_RESOURCE_TYPES_URL, {"q": "average"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["name"] == "Average"


def test_get_linked_resource_types_sortby_name_descending(client):
    LinkedResourceTypeFactory(global_=True, name="Alpha")
    LinkedResourceTypeFactory(global_=True, name="Beta")

    response = client.get(LINKED_RESOURCE_TYPES_URL, {"sortby": "-name"})

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]]
    assert names.index("Beta") < names.index("Alpha")


def test_get_linked_resource_types_is_active_filter(client):
    LinkedResourceTypeFactory(global_=True, name="Active term", is_active=True)
    LinkedResourceTypeFactory(global_=True, name="Inactive term", is_active=False)

    response = client.get(LINKED_RESOURCE_TYPES_URL, {"is_active": "true"})

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]]
    assert names == ["Active term"]


# --- create_linked_resource_type ------------------------------------------------------


def test_create_linked_resource_type_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        LINKED_RESOURCE_TYPES_URL,
        data=_linked_resource_type_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}
    linked_resource_type_id = response.json()["id"]

    detail = client.get(_detail_url(linked_resource_type_id))
    assert detail.json()["data"]["name"] == "New Term"
    assert detail.json()["data"]["isActive"] is True


def test_create_linked_resource_type_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        LINKED_RESOURCE_TYPES_URL,
        data=_linked_resource_type_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_linked_resource_type_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        LINKED_RESOURCE_TYPES_URL,
        data=_linked_resource_type_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_linked_resource_type_returns_400_for_duplicate_name_in_workspace(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    LinkedResourceTypeFactory(workspace=workspace, name="Duplicate")
    client.force_login(owner)

    response = client.post(
        LINKED_RESOURCE_TYPES_URL,
        data=_linked_resource_type_body(workspaceId=str(workspace.id), name="Duplicate"),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_linked_resource_type ----------------------------------------------------------


def test_get_linked_resource_type_returns_global_term_for_anonymous(client):
    linked_resource_type = LinkedResourceTypeFactory(global_=True)

    response = client.get(_detail_url(linked_resource_type.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(linked_resource_type.id)


def test_get_linked_resource_type_returns_404_for_private_workspace_term_when_unrelated(
    client,
):
    workspace = WorkspaceFactory(is_private=True)
    linked_resource_type = LinkedResourceTypeFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(linked_resource_type.id))

    assert response.status_code == 404


def test_get_linked_resource_type_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    linked_resource_type = LinkedResourceTypeFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(linked_resource_type.id))

    assert response.status_code == 200


def test_get_linked_resource_type_returns_404_for_nonexistent_term(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_linked_resource_type_include_workspace_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    linked_resource_type = LinkedResourceTypeFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(linked_resource_type.id), {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(linked_resource_type.id)
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_linked_resource_type_include_workspace_does_not_scale_queries_with_count(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    for i in range(5):
        LinkedResourceTypeFactory(workspace=workspace, name=f"A{i}")
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(LINKED_RESOURCE_TYPES_URL, {"include": "workspace"})

    for i in range(5):
        LinkedResourceTypeFactory(workspace=workspace, name=f"B{i}")

    with CaptureQueriesContext(connection) as large:
        client.get(LINKED_RESOURCE_TYPES_URL, {"include": "workspace"})

    assert len(large.captured_queries) == len(small.captured_queries)


# --- update_linked_resource_type -------------------------------------------------------


def test_update_linked_resource_type_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    linked_resource_type = LinkedResourceTypeFactory(workspace=workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(linked_resource_type.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(linked_resource_type.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_linked_resource_type_can_deprecate_a_term(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    linked_resource_type = LinkedResourceTypeFactory(workspace=workspace, is_active=True)
    client.force_login(owner)

    response = client.patch(
        _detail_url(linked_resource_type.id),
        data={"isActive": False},
        content_type="application/json",
    )

    assert response.status_code == 204

    detail = client.get(_detail_url(linked_resource_type.id))
    assert detail.json()["data"]["isActive"] is False


def test_update_linked_resource_type_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    linked_resource_type = LinkedResourceTypeFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(linked_resource_type.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_linked_resource_type -------------------------------------------------------


def test_delete_linked_resource_type_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    linked_resource_type = LinkedResourceTypeFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(linked_resource_type.id))

    assert response.status_code == 204
    assert client.get(_detail_url(linked_resource_type.id)).status_code == 404


def test_delete_linked_resource_type_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    linked_resource_type = LinkedResourceTypeFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(linked_resource_type.id))

    assert response.status_code == 403
