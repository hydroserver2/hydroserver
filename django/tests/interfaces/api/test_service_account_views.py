import pytest

from django.conf import settings
from django.test.utils import CaptureQueriesContext
from django.db import connection

from core.iam.models import Collaborator, ServiceAccount
from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    ServiceAccountFactory,
    UserFactory,
    WorkspaceFactory,
)

pytestmark = pytest.mark.django_db

SERVICE_ACCOUNT_FIELDS = {
    "id",
    "workspaceId",
    "name",
    "description",
    "isActive",
    "keyExpiresAt",
    "email",
    "createdAt",
    "lastUsedAt",
}


def _service_accounts_url(workspace_id):
    return f"/api/data/workspaces/{workspace_id}/service-accounts"


def _detail_url(workspace_id, service_account_id):
    return f"{_service_accounts_url(workspace_id)}/{service_account_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="ServiceAccount", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


# --- get_service_accounts ----------------------------------------------------


def test_get_service_accounts_includes_accounts_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_service_accounts_url(workspace.id))

    assert response.status_code == 200
    assert str(service_account.id) in [sa["id"] for sa in response.json()["data"]]


def test_get_service_accounts_returns_404_for_workspace_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_service_accounts_url(workspace.id))

    assert response.status_code == 404


def test_get_service_accounts_properties_filters_every_item_in_the_list(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ServiceAccountFactory(workspace=workspace)
    ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(
        _service_accounts_url(workspace.id), {"properties": "id,name"}
    )

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "name"}


def test_get_service_accounts_properties_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(
        _service_accounts_url(workspace.id), {"properties": ["id", "name"]}
    )

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name"}


def test_get_service_accounts_properties_rejects_unknown_property(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(
        _service_accounts_url(workspace.id), {"properties": "id,bogus"}
    )

    assert response.status_code == 400


def test_get_service_accounts_without_properties_returns_every_field(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_service_accounts_url(workspace.id))

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == SERVICE_ACCOUNT_FIELDS


def test_get_service_accounts_has_no_included_key_without_include_param(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_service_accounts_url(workspace.id))

    assert response.status_code == 200
    assert "included" not in response.json()


def test_get_service_accounts_include_workspace_deduplicates_across_items(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ServiceAccountFactory(workspace=workspace)
    ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_service_accounts_url(workspace.id), {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_service_accounts_include_rejects_unknown_relation(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(_service_accounts_url(workspace.id), {"include": "bogus"})

    assert response.status_code == 400


def test_get_service_accounts_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_service_accounts_url(workspace.id), {"include": ["workspace"]})

    assert response.status_code == 200
    body = response.json()
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_service_accounts_properties_and_include_together(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(
        _service_accounts_url(workspace.id),
        {"properties": "id,name", "include": "workspace"},
    )

    assert response.status_code == 200
    body = response.json()
    for item in body["data"]:
        assert set(item.keys()) == {"id", "name"}
    assert body["included"]["workspaces"][0]["id"] == str(workspace.id)


def test_get_service_accounts_properties_does_not_filter_included_resources(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner, name="Acme")
    ServiceAccountFactory(workspace=workspace, name="SA1")
    client.force_login(owner)

    response = client.get(
        _service_accounts_url(workspace.id),
        {"properties": "name", "include": "workspace"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0] == {"name": "SA1"}
    included_workspace = body["included"]["workspaces"][0]
    assert included_workspace["id"] == str(workspace.id)
    assert included_workspace["name"] == "Acme"


def test_get_service_accounts_include_workspace_does_not_scale_queries_with_account_count(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    for _ in range(5):
        ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(_service_accounts_url(workspace.id), {"include": "workspace"})

    for _ in range(5):
        ServiceAccountFactory(workspace=workspace)

    with CaptureQueriesContext(connection) as large:
        client.get(_service_accounts_url(workspace.id), {"include": "workspace"})

    assert len(large.captured_queries) == len(small.captured_queries)


# --- create_service_account ---------------------------------------------------


def test_create_service_account_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        _service_accounts_url(workspace.id),
        data={"name": "New Service Account", "isActive": True},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["key"]


def test_create_service_account_response_is_id_and_key_only(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        _service_accounts_url(workspace.id),
        data={"name": "New Service Account", "isActive": True},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id", "key"}

    detail = client.get(_detail_url(workspace.id, response.json()["id"]))
    body = detail.json()["data"]
    assert body["email"].endswith(
        f"@service-accounts.{settings.SERVICE_ACCOUNT_EMAIL_DOMAIN}"
    )
    assert "role" not in body
    assert "key" not in body


def test_create_service_account_include_workspace_sideloads_it_on_follow_up_get(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    create_response = client.post(
        _service_accounts_url(workspace.id),
        data={"name": "New Service Account", "isActive": True},
        content_type="application/json",
    )
    assert create_response.status_code == 201
    service_account_id = create_response.json()["id"]

    response = client.get(
        _detail_url(workspace.id, service_account_id), {"include": "workspace"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["included"]["workspaces"][0]["id"] == str(workspace.id)
    assert body["included"]["workspaces"][0]["ownerEmail"] == owner.email


def test_create_service_account_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        _service_accounts_url(workspace.id),
        data={"name": "New Service Account", "isActive": True},
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_service_account_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        _service_accounts_url(workspace.id),
        data={"name": "New Service Account", "isActive": True},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_service_account_with_role_id_creates_collaborator(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    role = RoleFactory(workspace=None)
    client.force_login(owner)

    response = client.post(
        _service_accounts_url(workspace.id),
        data={"name": "New Service Account", "isActive": True, "roleId": str(role.id)},
        content_type="application/json",
    )

    assert response.status_code == 201
    service_account_id = response.json()["id"]
    assert Collaborator.objects.filter(
        workspace=workspace, service_account_id=service_account_id, role=role
    ).exists()


def test_create_service_account_with_role_from_other_workspace_returns_400_without_orphaning(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    other_workspace = WorkspaceFactory(owner=owner)
    other_role = RoleFactory(workspace=other_workspace)
    client.force_login(owner)

    response = client.post(
        _service_accounts_url(workspace.id),
        data={
            "name": "New Service Account",
            "isActive": True,
            "roleId": str(other_role.id),
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert not ServiceAccount.objects.filter(workspace=workspace).exists()


def test_create_service_account_with_role_id_without_collaborator_permission_returns_403_without_orphaning(client):
    workspace = WorkspaceFactory()
    role = RoleFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_create=True)
    client.force_login(collaborator.user)

    response = client.post(
        _service_accounts_url(workspace.id),
        data={"name": "New Service Account", "isActive": True, "roleId": str(role.id)},
        content_type="application/json",
    )

    assert response.status_code == 403
    assert not ServiceAccount.objects.filter(workspace=workspace).exists()


# --- get_service_account --------------------------------------------------------


def test_get_service_account_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(workspace.id, service_account.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(service_account.id)


def test_get_service_account_returns_404_for_workspace_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    service_account = ServiceAccountFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(workspace.id, service_account.id))

    assert response.status_code == 404


def test_get_service_account_returns_404_for_nonexistent_account(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(
        _detail_url(workspace.id, "00000000-0000-0000-0000-000000000000")
    )

    assert response.status_code == 404


def test_get_service_account_properties_rejects_unknown_property(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(
        _detail_url(workspace.id, service_account.id), {"properties": "bogus"}
    )

    assert response.status_code == 400


def test_get_service_account_included_is_present_but_empty_without_include_param(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(workspace.id, service_account.id))

    assert response.status_code == 200
    body = response.json()
    assert "included" in body
    assert body["included"] == {}


def test_get_service_account_include_workspace_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(
        _detail_url(workspace.id, service_account.id), {"include": "workspace"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(service_account.id)
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_service_account_include_rejects_unknown_relation(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(
        _detail_url(workspace.id, service_account.id), {"include": "bogus"}
    )

    assert response.status_code == 400


def test_get_service_account_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(
        _detail_url(workspace.id, service_account.id), {"include": ["workspace"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


# --- update_service_account ---------------------------------------------------


def test_update_service_account_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(workspace.id, service_account.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(workspace.id, service_account.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_service_account_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    service_account = ServiceAccountFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(workspace.id, service_account.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_service_account ---------------------------------------------------


def test_delete_service_account_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(workspace.id, service_account.id))

    assert response.status_code == 204
    assert client.get(_detail_url(workspace.id, service_account.id)).status_code == 404


def test_delete_service_account_returns_403_without_delete_permission(client):
    workspace = WorkspaceFactory()
    service_account = ServiceAccountFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(workspace.id, service_account.id))

    assert response.status_code == 403


# --- regenerate_service_account_key --------------------------------------------


def test_regenerate_service_account_key_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    service_account = ServiceAccountFactory(workspace=workspace)
    client.force_login(owner)

    response = client.put(f"{_detail_url(workspace.id, service_account.id)}/regenerate")

    assert response.status_code == 201
    assert response.json()["key"]
    assert set(response.json().keys()) == {"key"}


def test_regenerate_service_account_key_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    service_account = ServiceAccountFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.put(f"{_detail_url(workspace.id, service_account.id)}/regenerate")

    assert response.status_code == 403
