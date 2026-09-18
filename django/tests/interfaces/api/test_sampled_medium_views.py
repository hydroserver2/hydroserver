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
from tests.core.sta.factories import SampledMediumFactory

pytestmark = pytest.mark.django_db

SAMPLED_MEDIUMS_URL = "/api/data/sampled-mediums"


def _detail_url(sampled_medium_id):
    return f"{SAMPLED_MEDIUMS_URL}/{sampled_medium_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="SampledMedium", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _sampled_medium_body(**overrides):
    body = {
        "name": "New Medium",
        "description": "A new sampled medium.",
    }
    body.update(overrides)
    return body


# --- get_sampled_mediums --------------------------------------------------------------


def test_get_sampled_mediums_includes_global_terms_for_anonymous(client):
    sampled_medium = SampledMediumFactory(global_=True)

    response = client.get(SAMPLED_MEDIUMS_URL)

    assert response.status_code == 200
    assert str(sampled_medium.id) in [r["id"] for r in response.json()["data"]]


def test_get_sampled_mediums_excludes_private_workspace_terms_for_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    SampledMediumFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(SAMPLED_MEDIUMS_URL)

    assert response.json()["data"] == []


def test_get_sampled_mediums_includes_workspace_terms_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    sampled_medium = SampledMediumFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(SAMPLED_MEDIUMS_URL)

    assert response.status_code == 200
    assert str(sampled_medium.id) in [r["id"] for r in response.json()["data"]]


def test_get_sampled_mediums_properties_filters_every_item_in_the_list(client):
    SampledMediumFactory(global_=True, name="A")
    SampledMediumFactory(global_=True, name="B")

    response = client.get(SAMPLED_MEDIUMS_URL, {"properties": "id,name"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "name"}


def test_get_sampled_mediums_properties_rejects_unknown_property(client):
    response = client.get(SAMPLED_MEDIUMS_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_sampled_mediums_without_properties_returns_every_field(client):
    SampledMediumFactory(global_=True, name="A")

    response = client.get(SAMPLED_MEDIUMS_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name", "description", "isActive", "workspaceId"}


def test_get_sampled_mediums_has_no_included_key_without_include_param(client):
    SampledMediumFactory(global_=True)

    response = client.get(SAMPLED_MEDIUMS_URL)

    assert response.status_code == 200
    assert "included" not in response.json()


def test_get_sampled_mediums_include_workspace_deduplicates_across_items(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    SampledMediumFactory(workspace=workspace, name="A")
    SampledMediumFactory(workspace=workspace, name="B")
    client.force_login(owner)

    response = client.get(SAMPLED_MEDIUMS_URL, {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_sampled_mediums_include_rejects_unknown_relation(client):
    response = client.get(SAMPLED_MEDIUMS_URL, {"include": "bogus"})

    assert response.status_code == 400


def test_get_sampled_mediums_include_workspace_does_not_scale_queries_with_count(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    for i in range(5):
        SampledMediumFactory(workspace=workspace, name=f"A{i}")
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(SAMPLED_MEDIUMS_URL, {"include": "workspace"})

    for i in range(5):
        SampledMediumFactory(workspace=workspace, name=f"B{i}")

    with CaptureQueriesContext(connection) as large:
        client.get(SAMPLED_MEDIUMS_URL, {"include": "workspace"})

    assert len(large.captured_queries) == len(small.captured_queries)


def test_get_sampled_mediums_q_searches_name_and_description(client):
    SampledMediumFactory(global_=True, name="Surface water", description="")
    SampledMediumFactory(global_=True, name="Groundwater", description="")

    response = client.get(SAMPLED_MEDIUMS_URL, {"q": "surface"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["name"] == "Surface water"


def test_get_sampled_mediums_sortby_name_descending(client):
    SampledMediumFactory(global_=True, name="Alpha")
    SampledMediumFactory(global_=True, name="Beta")

    response = client.get(SAMPLED_MEDIUMS_URL, {"sortby": "-name"})

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]]
    assert names.index("Beta") < names.index("Alpha")


def test_get_sampled_mediums_is_active_filter(client):
    SampledMediumFactory(global_=True, name="Active term", is_active=True)
    SampledMediumFactory(global_=True, name="Inactive term", is_active=False)

    response = client.get(SAMPLED_MEDIUMS_URL, {"is_active": "true"})

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]]
    assert names == ["Active term"]


# --- create_sampled_medium ------------------------------------------------------------


def test_create_sampled_medium_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        SAMPLED_MEDIUMS_URL,
        data=_sampled_medium_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}
    sampled_medium_id = response.json()["id"]

    detail = client.get(_detail_url(sampled_medium_id))
    assert detail.json()["data"]["name"] == "New Medium"
    assert detail.json()["data"]["isActive"] is True


def test_create_sampled_medium_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        SAMPLED_MEDIUMS_URL,
        data=_sampled_medium_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_sampled_medium_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        SAMPLED_MEDIUMS_URL,
        data=_sampled_medium_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_sampled_medium_returns_400_for_duplicate_name_in_workspace(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    SampledMediumFactory(workspace=workspace, name="Duplicate")
    client.force_login(owner)

    response = client.post(
        SAMPLED_MEDIUMS_URL,
        data=_sampled_medium_body(workspaceId=str(workspace.id), name="Duplicate"),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_sampled_medium_returns_400_for_duplicate_name_even_when_existing_is_inactive(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    SampledMediumFactory(workspace=workspace, name="Duplicate", is_active=False)
    client.force_login(owner)

    response = client.post(
        SAMPLED_MEDIUMS_URL,
        data=_sampled_medium_body(workspaceId=str(workspace.id), name="Duplicate"),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_sampled_medium ----------------------------------------------------------------


def test_get_sampled_medium_returns_global_term_for_anonymous(client):
    sampled_medium = SampledMediumFactory(global_=True)

    response = client.get(_detail_url(sampled_medium.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(sampled_medium.id)


def test_get_sampled_medium_returns_404_for_private_workspace_term_when_unrelated(client):
    workspace = WorkspaceFactory(is_private=True)
    sampled_medium = SampledMediumFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(sampled_medium.id))

    assert response.status_code == 404


def test_get_sampled_medium_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    sampled_medium = SampledMediumFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(sampled_medium.id))

    assert response.status_code == 200


def test_get_sampled_medium_returns_404_for_nonexistent_term(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_sampled_medium_included_is_present_but_empty_without_include_param(client):
    sampled_medium = SampledMediumFactory(global_=True)

    response = client.get(_detail_url(sampled_medium.id))

    assert response.status_code == 200
    body = response.json()
    assert "included" in body
    assert body["included"] == {}


def test_get_sampled_medium_include_workspace_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    sampled_medium = SampledMediumFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(sampled_medium.id), {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(sampled_medium.id)
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_sampled_medium_include_rejects_unknown_relation(client):
    sampled_medium = SampledMediumFactory(global_=True)

    response = client.get(_detail_url(sampled_medium.id), {"include": "bogus"})

    assert response.status_code == 400


def test_get_sampled_medium_properties_rejects_unknown_property(client):
    sampled_medium = SampledMediumFactory(global_=True)

    response = client.get(_detail_url(sampled_medium.id), {"properties": "bogus"})

    assert response.status_code == 400


# --- update_sampled_medium -------------------------------------------------------------


def test_update_sampled_medium_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    sampled_medium = SampledMediumFactory(workspace=workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(sampled_medium.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(sampled_medium.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_sampled_medium_can_deprecate_a_term(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    sampled_medium = SampledMediumFactory(workspace=workspace, is_active=True)
    client.force_login(owner)

    response = client.patch(
        _detail_url(sampled_medium.id),
        data={"isActive": False},
        content_type="application/json",
    )

    assert response.status_code == 204

    detail = client.get(_detail_url(sampled_medium.id))
    assert detail.json()["data"]["isActive"] is False
    assert detail.json()["data"]["name"] == sampled_medium.name


def test_update_sampled_medium_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    sampled_medium = SampledMediumFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(sampled_medium.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_sampled_medium -------------------------------------------------------------


def test_delete_sampled_medium_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    sampled_medium = SampledMediumFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(sampled_medium.id))

    assert response.status_code == 204
    assert client.get(_detail_url(sampled_medium.id)).status_code == 404


def test_delete_sampled_medium_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    sampled_medium = SampledMediumFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(sampled_medium.id))

    assert response.status_code == 403
