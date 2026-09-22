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
from tests.core.sta.factories import (
    DatastreamFactory,
    ObservedPropertyFactory,
    ObservedPropertyTypeFactory,
)

pytestmark = pytest.mark.django_db

OBSERVED_PROPERTIES_URL = "/api/data/observed-properties"


def _detail_url(observed_property_id):
    return f"{OBSERVED_PROPERTIES_URL}/{observed_property_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="ObservedProperty", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _observed_property_body(**overrides):
    body = {
        "name": "New Observed Property",
        "definition": "https://example.com/def",
        "description": "A new observed property.",
        "type": "Hydrology",
        "code": "OP-NEW",
    }
    body.update(overrides)
    return body


# --- get_observed_properties ---------------------------------------------------------


def test_get_observed_properties_includes_global_properties_for_anonymous(client):
    observed_property = ObservedPropertyFactory(global_=True)

    response = client.get(OBSERVED_PROPERTIES_URL)

    assert response.status_code == 200
    assert str(observed_property.id) in [o["id"] for o in response.json()["data"]]


def test_get_observed_properties_excludes_private_workspace_properties_for_outsider(
    client,
):
    workspace = WorkspaceFactory(is_private=True)
    ObservedPropertyFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(OBSERVED_PROPERTIES_URL)

    assert response.json()["data"] == []


def test_get_observed_properties_includes_workspace_properties_for_workspace_owner(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(OBSERVED_PROPERTIES_URL)

    assert response.status_code == 200
    assert str(observed_property.id) in [o["id"] for o in response.json()["data"]]


def test_get_observed_properties_filters_by_type(client):
    hydrology = ObservedPropertyFactory(global_=True, type="Hydrology")
    ObservedPropertyFactory(global_=True, type="Meteorology")

    response = client.get(OBSERVED_PROPERTIES_URL, {"type": "Hydrology"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(hydrology.id)]


def test_get_observed_properties_properties_filters_every_item_in_the_list(client):
    ObservedPropertyFactory(global_=True, name="Temperature")
    ObservedPropertyFactory(global_=True, name="Discharge")

    response = client.get(OBSERVED_PROPERTIES_URL, {"properties": "id,name"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "name"}


def test_get_observed_properties_properties_accepts_repeated_key_style_too(client):
    ObservedPropertyFactory(global_=True, name="Temperature")

    response = client.get(OBSERVED_PROPERTIES_URL, {"properties": ["id", "name"]})

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name"}


def test_get_observed_properties_properties_rejects_unknown_property(client):
    response = client.get(OBSERVED_PROPERTIES_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_observed_properties_without_properties_returns_every_field(client):
    ObservedPropertyFactory(global_=True, name="Temperature", type="Hydrology")

    response = client.get(OBSERVED_PROPERTIES_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {
        "id",
        "name",
        "definition",
        "description",
        "type",
        "code",
        "workspaceId",
    }


def test_get_observed_properties_has_no_included_key_without_include_param(client):
    ObservedPropertyFactory(global_=True)

    response = client.get(OBSERVED_PROPERTIES_URL)

    assert response.status_code == 200
    assert "included" not in response.json()


def test_get_observed_properties_include_workspace_deduplicates_across_items(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ObservedPropertyFactory(workspace=workspace, name="Temperature")
    ObservedPropertyFactory(workspace=workspace, name="Discharge")
    client.force_login(owner)

    response = client.get(OBSERVED_PROPERTIES_URL, {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_observed_properties_include_type_sideloads_observed_property_type(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    observed_property_type = ObservedPropertyTypeFactory(name="Hydrology")
    ObservedPropertyFactory(workspace=workspace, type=observed_property_type.name)
    client.force_login(owner)

    response = client.get(OBSERVED_PROPERTIES_URL, {"include": "type"})

    assert response.status_code == 200
    included = response.json()["included"]
    assert {row["id"] for row in included["observedPropertyTypes"]} == {
        str(observed_property_type.id)
    }


def test_get_observed_properties_include_rejects_unknown_relation(client):
    response = client.get(OBSERVED_PROPERTIES_URL, {"include": "bogus"})

    assert response.status_code == 400


def test_get_observed_properties_properties_does_not_filter_included_resources(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner, name="Acme")
    ObservedPropertyFactory(workspace=workspace, code="OP-1")
    client.force_login(owner)

    response = client.get(
        OBSERVED_PROPERTIES_URL, {"properties": "code", "include": "workspace"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0] == {"code": "OP-1"}
    included_workspace = body["included"]["workspaces"][0]
    assert included_workspace["id"] == str(workspace.id)
    assert included_workspace["name"] == "Acme"


def test_get_observed_properties_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ObservedPropertyFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(OBSERVED_PROPERTIES_URL, {"include": ["workspace"]})

    assert response.status_code == 200
    body = response.json()
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_observed_properties_include_workspace_does_not_scale_queries_with_count(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    for _ in range(5):
        ObservedPropertyFactory(workspace=workspace)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(OBSERVED_PROPERTIES_URL, {"include": "workspace"})

    for _ in range(5):
        ObservedPropertyFactory(workspace=workspace)

    with CaptureQueriesContext(connection) as large:
        client.get(OBSERVED_PROPERTIES_URL, {"include": "workspace"})

    assert len(large.captured_queries) == len(small.captured_queries)


# --- create_observed_property ---------------------------------------------------------


def test_create_observed_property_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        OBSERVED_PROPERTIES_URL,
        data=_observed_property_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}


def test_create_observed_property_allows_omitting_definition(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)
    body = _observed_property_body(workspaceId=str(workspace.id))
    body.pop("definition")

    response = client.post(
        OBSERVED_PROPERTIES_URL,
        data=body,
        content_type="application/json",
    )

    assert response.status_code == 201
    observed_property_id = response.json()["id"]

    detail = client.get(_detail_url(observed_property_id), {"properties": "definition"})
    assert detail.json()["data"]["definition"] is None


@pytest.mark.parametrize("field", ["type", "code"])
def test_create_observed_property_allows_500_character_type_and_code(client, field):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)
    value = "x" * 500

    response = client.post(
        OBSERVED_PROPERTIES_URL,
        data=_observed_property_body(
            workspaceId=str(workspace.id),
            **{field: value},
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    observed_property_id = response.json()["id"]

    detail = client.get(_detail_url(observed_property_id), {"properties": field})
    assert detail.json()["data"][field] == value


def test_create_observed_property_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        OBSERVED_PROPERTIES_URL,
        data=_observed_property_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_observed_property_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        OBSERVED_PROPERTIES_URL,
        data=_observed_property_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 403


# --- get_observed_property -------------------------------------------------------------


def test_get_observed_property_returns_global_property_for_anonymous(client):
    observed_property = ObservedPropertyFactory(global_=True)

    response = client.get(_detail_url(observed_property.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(observed_property.id)


def test_get_observed_property_returns_404_for_private_workspace_property_when_unrelated(
    client,
):
    workspace = WorkspaceFactory(is_private=True)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(observed_property.id))

    assert response.status_code == 404


def test_get_observed_property_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(observed_property.id))

    assert response.status_code == 200


def test_get_observed_property_returns_404_for_nonexistent_property(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_observed_property_included_is_present_but_empty_without_include_param(
    client,
):
    observed_property = ObservedPropertyFactory(global_=True)

    response = client.get(_detail_url(observed_property.id))

    assert response.status_code == 200
    body = response.json()
    assert "included" in body
    assert body["included"] == {}


def test_get_observed_property_include_workspace_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(observed_property.id), {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(observed_property.id)
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_observed_property_include_rejects_unknown_relation(client):
    observed_property = ObservedPropertyFactory(global_=True)

    response = client.get(_detail_url(observed_property.id), {"include": "bogus"})

    assert response.status_code == 400


def test_get_observed_property_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(observed_property.id), {"include": ["workspace"]})

    assert response.status_code == 200
    body = response.json()
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_observed_property_properties_rejects_unknown_property(client):
    observed_property = ObservedPropertyFactory(global_=True)

    response = client.get(_detail_url(observed_property.id), {"properties": "bogus"})

    assert response.status_code == 400


# --- update_observed_property -----------------------------------------------------------


def test_update_observed_property_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    observed_property = ObservedPropertyFactory(
        workspace=workspace, name="Original Name"
    )
    client.force_login(owner)

    response = client.patch(
        _detail_url(observed_property.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(observed_property.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_observed_property_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    observed_property = ObservedPropertyFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(observed_property.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_observed_property -----------------------------------------------------------


def test_delete_observed_property_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(observed_property.id))

    assert response.status_code == 204
    assert client.get(_detail_url(observed_property.id)).status_code == 404


def test_delete_observed_property_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    observed_property = ObservedPropertyFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(observed_property.id))

    assert response.status_code == 403


def test_delete_observed_property_returns_409_when_in_use_by_datastream(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    DatastreamFactory(observed_property=observed_property)
    client.force_login(owner)

    response = client.delete(_detail_url(observed_property.id))

    assert response.status_code == 409
