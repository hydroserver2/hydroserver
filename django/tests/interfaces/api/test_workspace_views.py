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

pytestmark = pytest.mark.django_db

WORKSPACES_URL = "/api/data/workspaces"

WORKSPACE_FIELDS = {
    "id",
    "name",
    "isPrivate",
    "ownerEmail",
    "pendingTransferToEmail",
    "collaboratorRoleId",
}


def _detail_url(workspace_id):
    return f"{WORKSPACES_URL}/{workspace_id}"


def _transfer_url(workspace_id):
    return f"{WORKSPACES_URL}/{workspace_id}/transfer"


def _viewer_collaborator(workspace):
    """A collaborator who can view this workspace but not edit or delete it."""

    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Workspace", can_view=True)
    return CollaboratorFactory(workspace=workspace, role=role)


# --- get_workspace --------------------------------------------------------------


def test_get_workspace_returns_workspace_for_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(_detail_url(workspace.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(workspace.id)
    assert response.json()["data"]["ownerEmail"] == owner.email


def test_get_workspace_returns_404_for_user_without_access(client):
    workspace = WorkspaceFactory(is_private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(workspace.id))

    assert response.status_code == 404


def test_get_workspace_returns_404_for_nonexistent_workspace(client):
    user = UserFactory()
    client.force_login(user)

    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_workspace_properties_rejects_unknown_property(client):
    workspace = WorkspaceFactory()
    client.force_login(workspace.owner)

    response = client.get(_detail_url(workspace.id), {"properties": "bogus"})

    assert response.status_code == 400


def test_get_workspace_without_properties_returns_every_field(client):
    workspace = WorkspaceFactory()
    client.force_login(workspace.owner)

    response = client.get(_detail_url(workspace.id))

    assert response.status_code == 200
    assert set(response.json()["data"].keys()) == WORKSPACE_FIELDS


def test_get_workspace_included_is_present_but_empty_without_include_param(client):
    workspace = WorkspaceFactory()
    client.force_login(workspace.owner)

    response = client.get(_detail_url(workspace.id))

    assert response.status_code == 200
    body = response.json()
    assert "included" in body
    assert body["included"] == {}


def test_get_workspace_include_owner_sideloads_it(client):
    workspace = WorkspaceFactory()
    client.force_login(workspace.owner)

    response = client.get(_detail_url(workspace.id), {"include": "owner"})

    assert response.status_code == 200
    body = response.json()
    assert [o["email"] for o in body["included"]["owners"]] == [workspace.owner.email]


def test_get_workspace_include_pending_transfer_to_sideloads_for_recipient(client):
    owner = UserFactory()
    recipient = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    workspace.initiate_transfer(recipient)
    client.force_login(recipient)

    response = client.get(_detail_url(workspace.id), {"include": "pendingTransferTo"})

    assert response.status_code == 200
    body = response.json()
    assert [u["email"] for u in body["included"]["pendingTransferRecipients"]] == [
        recipient.email
    ]
    assert body["data"]["pendingTransferToEmail"] == recipient.email


def test_get_workspace_include_pending_transfer_to_absent_without_active_transfer(
    client,
):
    workspace = WorkspaceFactory()
    client.force_login(workspace.owner)

    response = client.get(_detail_url(workspace.id), {"include": "pendingTransferTo"})

    assert response.status_code == 200
    body = response.json()
    assert body["included"] == {}
    assert body["data"]["pendingTransferToEmail"] is None


def test_get_workspace_include_collaborator_role_sideloads_for_collaborator(client):
    workspace = WorkspaceFactory()
    collaborator = _viewer_collaborator(workspace)
    client.force_login(collaborator.user)

    response = client.get(_detail_url(workspace.id), {"include": "collaboratorRole"})

    assert response.status_code == 200
    body = response.json()
    assert body["included"]["collaboratorRoles"][0]["permissions"] == [
        {"resource": "Workspace", "action": "view"}
    ]
    assert body["data"]["collaboratorRoleId"] == str(collaborator.role.id)


def test_get_workspace_include_collaborator_role_absent_for_owner(client):
    workspace = WorkspaceFactory()
    client.force_login(workspace.owner)

    response = client.get(_detail_url(workspace.id), {"include": "collaboratorRole"})

    assert response.status_code == 200
    body = response.json()
    assert body["included"] == {}
    assert body["data"]["collaboratorRoleId"] is None


def test_get_workspace_include_rejects_unknown_relation(client):
    workspace = WorkspaceFactory()
    client.force_login(workspace.owner)

    response = client.get(_detail_url(workspace.id), {"include": "bogus"})

    assert response.status_code == 400


def test_get_workspace_include_accepts_repeated_key_style_too(client):
    workspace = WorkspaceFactory()
    client.force_login(workspace.owner)

    response = client.get(_detail_url(workspace.id), {"include": ["owner"]})

    assert response.status_code == 200
    body = response.json()
    assert [o["email"] for o in body["included"]["owners"]] == [workspace.owner.email]


# --- create_workspace ------------------------------------------------------------


def test_create_workspace_succeeds_for_authenticated_user(client):
    user = UserFactory()
    client.force_login(user)

    response = client.post(
        WORKSPACES_URL,
        data={"name": "New Workspace", "isPrivate": False},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}


def test_create_workspace_returns_401_when_unauthenticated(client):
    response = client.post(
        WORKSPACES_URL,
        data={"name": "New Workspace", "isPrivate": False},
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_workspace_returns_400_for_duplicate_name_owned_by_user(client):
    owner = UserFactory()
    WorkspaceFactory(owner=owner, name="Existing Workspace")
    client.force_login(owner)

    response = client.post(
        WORKSPACES_URL,
        data={"name": "Existing Workspace", "isPrivate": False},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_workspace_returns_400_when_owner_at_workspace_limit(client):
    owner = UserFactory(owned_workspace_limit=1)
    WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        WORKSPACES_URL,
        data={"name": "Second Workspace", "isPrivate": False},
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_workspaces ---------------------------------------------------------------


def test_get_workspaces_includes_workspaces_owned_by_the_user(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(WORKSPACES_URL)

    assert response.status_code == 200
    assert str(workspace.id) in [w["id"] for w in response.json()["data"]]


def test_get_workspaces_excludes_private_workspaces_of_others(client):
    WorkspaceFactory(is_private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(WORKSPACES_URL)

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_get_workspaces_properties_filters_every_item_in_the_list(client):
    owner = UserFactory()
    WorkspaceFactory(owner=owner, name="Acme")
    WorkspaceFactory(owner=owner, name="Beta")
    client.force_login(owner)

    response = client.get(WORKSPACES_URL, {"properties": "id,name"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "name"}


def test_get_workspaces_properties_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    WorkspaceFactory(owner=owner, name="Acme")
    client.force_login(owner)

    response = client.get(WORKSPACES_URL, {"properties": ["id", "name"]})

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name"}


def test_get_workspaces_properties_rejects_unknown_property(client):
    response = client.get(WORKSPACES_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_workspaces_without_properties_returns_every_field(client):
    owner = UserFactory()
    WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(WORKSPACES_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == WORKSPACE_FIELDS


def test_get_workspaces_has_no_included_key_without_include_param(client):
    owner = UserFactory()
    WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(WORKSPACES_URL)

    assert response.status_code == 200
    assert "included" not in response.json()


def test_get_workspaces_include_owner_deduplicates_across_items(client):
    owner = UserFactory()
    WorkspaceFactory(owner=owner, name="Acme")
    WorkspaceFactory(owner=owner, name="Beta")
    client.force_login(owner)

    response = client.get(WORKSPACES_URL, {"include": "owner"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert [o["email"] for o in body["included"]["owners"]] == [owner.email]


def test_get_workspaces_include_rejects_unknown_relation(client):
    response = client.get(WORKSPACES_URL, {"include": "bogus"})

    assert response.status_code == 400


def test_get_workspaces_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(WORKSPACES_URL, {"include": ["owner"]})

    assert response.status_code == 200
    body = response.json()
    assert [o["email"] for o in body["included"]["owners"]] == [owner.email]


def test_get_workspaces_properties_and_include_together(client):
    owner = UserFactory()
    WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(
        WORKSPACES_URL, {"properties": "id,name", "include": "owner"}
    )

    assert response.status_code == 200
    body = response.json()
    for item in body["data"]:
        assert set(item.keys()) == {"id", "name"}
    assert body["included"]["owners"][0]["email"] == owner.email


def test_get_workspaces_properties_does_not_filter_included_resources(client):
    owner = UserFactory()
    WorkspaceFactory(owner=owner, name="Acme")
    client.force_login(owner)

    response = client.get(
        WORKSPACES_URL, {"properties": "name", "include": "owner"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0] == {"name": "Acme"}
    included_owner = body["included"]["owners"][0]
    assert included_owner["email"] == owner.email
    assert "name" in included_owner


def test_get_workspaces_include_pending_transfer_to_sideloads_for_recipient(client):
    owner = UserFactory()
    recipient = UserFactory()
    workspace = WorkspaceFactory(owner=owner, is_private=True)
    workspace.initiate_transfer(recipient)
    client.force_login(recipient)

    response = client.get(
        WORKSPACES_URL,
        {"is_associated": True, "include": "pendingTransferTo"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["id"] == str(workspace.id)
    assert body["data"][0]["pendingTransferToEmail"] == recipient.email
    assert [u["email"] for u in body["included"]["pendingTransferRecipients"]] == [
        recipient.email
    ]


def test_get_workspaces_include_collaborator_role_sideloads_for_collaborator(client):
    workspace = WorkspaceFactory()
    collaborator = _viewer_collaborator(workspace)
    client.force_login(collaborator.user)

    response = client.get(
        WORKSPACES_URL,
        {"is_associated": True, "include": "collaboratorRole"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["collaboratorRoleId"] == str(collaborator.role.id)
    assert body["included"]["collaboratorRoles"][0]["permissions"] == [
        {"resource": "Workspace", "action": "view"}
    ]


def test_get_workspaces_include_all_three_does_not_scale_queries_with_workspace_count(
    client,
):
    owner = UserFactory()
    for _ in range(5):
        WorkspaceFactory(owner=owner)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(
            WORKSPACES_URL,
            {"include": "owner,pendingTransferTo,collaboratorRole"},
        )

    for _ in range(5):
        WorkspaceFactory(owner=owner)

    with CaptureQueriesContext(connection) as large:
        client.get(
            WORKSPACES_URL,
            {"include": "owner,pendingTransferTo,collaboratorRole"},
        )

    assert len(large.captured_queries) == len(small.captured_queries)


# --- update_workspace ---------------------------------------------------------------


def test_update_workspace_succeeds_for_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(workspace.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(workspace.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_workspace_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    collaborator = _viewer_collaborator(workspace)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(workspace.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_update_workspace_returns_400_for_blank_name(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.patch(
        _detail_url(workspace.id),
        data={"name": ""},
        content_type="application/json",
    )

    assert response.status_code == 400


# --- delete_workspace ---------------------------------------------------------------


def test_delete_workspace_succeeds_for_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.delete(_detail_url(workspace.id))

    assert response.status_code == 204
    assert client.get(_detail_url(workspace.id)).status_code == 404


def test_delete_workspace_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    collaborator = _viewer_collaborator(workspace)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(workspace.id))

    assert response.status_code == 403


# --- transfer_workspace ---------------------------------------------------------------


def test_transfer_workspace_succeeds_for_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    new_owner = UserFactory()
    client.force_login(owner)

    response = client.post(
        _transfer_url(workspace.id),
        data={"newOwner": new_owner.email},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert workspace.transfer_confirmation.new_owner == new_owner


def test_transfer_workspace_returns_400_when_transferring_to_self(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        _transfer_url(workspace.id),
        data={"newOwner": owner.email},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_transfer_workspace_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    collaborator = _viewer_collaborator(workspace)
    new_owner = UserFactory()
    client.force_login(collaborator.user)

    response = client.post(
        _transfer_url(workspace.id),
        data={"newOwner": new_owner.email},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- accept_workspace_transfer ---------------------------------------------------------


def test_accept_workspace_transfer_succeeds_for_new_owner(client):
    owner = UserFactory()
    new_owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    workspace.initiate_transfer(new_owner)
    client.force_login(new_owner)

    response = client.put(_transfer_url(workspace.id))

    assert response.status_code == 200
    workspace.refresh_from_db()
    assert workspace.owner == new_owner


def test_accept_workspace_transfer_returns_400_when_none_pending(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.put(_transfer_url(workspace.id))

    assert response.status_code == 400


# --- reject_workspace_transfer ---------------------------------------------------------


def test_reject_workspace_transfer_succeeds_for_owner(client):
    owner = UserFactory()
    new_owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    workspace.initiate_transfer(new_owner)
    client.force_login(owner)

    response = client.delete(_transfer_url(workspace.id))

    assert response.status_code == 200
    workspace.refresh_from_db()
    assert workspace.owner == owner
    assert workspace.transfer is None


def test_reject_workspace_transfer_returns_400_when_none_pending(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.delete(_transfer_url(workspace.id))

    assert response.status_code == 400
