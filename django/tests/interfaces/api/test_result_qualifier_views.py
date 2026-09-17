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
from tests.core.sta.factories import ResultQualifierFactory

pytestmark = pytest.mark.django_db

RESULT_QUALIFIERS_URL = "/api/data/result-qualifiers"


def _detail_url(result_qualifier_id):
    return f"{RESULT_QUALIFIERS_URL}/{result_qualifier_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="ResultQualifier", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _result_qualifier_body(**overrides):
    body = {
        "code": "New Qualifier",
        "description": "A new result qualifier.",
    }
    body.update(overrides)
    return body


# --- get_result_qualifiers ----------------------------------------------------------


def test_get_result_qualifiers_includes_global_qualifiers_for_anonymous(client):
    result_qualifier = ResultQualifierFactory(global_=True)

    response = client.get(RESULT_QUALIFIERS_URL)

    assert response.status_code == 200
    assert str(result_qualifier.id) in [r["id"] for r in response.json()["data"]]


def test_get_result_qualifiers_excludes_private_workspace_qualifiers_for_outsider(
    client,
):
    workspace = WorkspaceFactory(is_private=True)
    ResultQualifierFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(RESULT_QUALIFIERS_URL)

    assert response.json()["data"] == []


def test_get_result_qualifiers_includes_workspace_qualifiers_for_workspace_owner(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    result_qualifier = ResultQualifierFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(RESULT_QUALIFIERS_URL)

    assert response.status_code == 200
    assert str(result_qualifier.id) in [r["id"] for r in response.json()["data"]]


def test_get_result_qualifiers_properties_filters_every_item_in_the_list(client):
    ResultQualifierFactory(global_=True, code="A")
    ResultQualifierFactory(global_=True, code="B")

    response = client.get(RESULT_QUALIFIERS_URL, {"properties": "id,code"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "code"}


def test_get_result_qualifiers_properties_accepts_repeated_key_style_too(client):
    ResultQualifierFactory(global_=True, code="A")

    response = client.get(RESULT_QUALIFIERS_URL, {"properties": ["id", "code"]})

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "code"}


def test_get_result_qualifiers_properties_rejects_unknown_property(client):
    response = client.get(RESULT_QUALIFIERS_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_result_qualifiers_without_properties_returns_every_field(client):
    ResultQualifierFactory(global_=True, code="A")

    response = client.get(RESULT_QUALIFIERS_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "code", "description", "workspaceId"}


def test_get_result_qualifiers_has_no_included_key_without_include_param(client):
    ResultQualifierFactory(global_=True)

    response = client.get(RESULT_QUALIFIERS_URL)

    assert response.status_code == 200
    assert "included" not in response.json()


def test_get_result_qualifiers_include_workspace_deduplicates_across_items(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ResultQualifierFactory(workspace=workspace, code="A")
    ResultQualifierFactory(workspace=workspace, code="B")
    client.force_login(owner)

    response = client.get(RESULT_QUALIFIERS_URL, {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_result_qualifiers_include_rejects_unknown_relation(client):
    response = client.get(RESULT_QUALIFIERS_URL, {"include": "bogus"})

    assert response.status_code == 400


def test_get_result_qualifiers_properties_does_not_filter_included_resources(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner, name="Acme")
    ResultQualifierFactory(workspace=workspace, code="A")
    client.force_login(owner)

    response = client.get(
        RESULT_QUALIFIERS_URL, {"properties": "code", "include": "workspace"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0] == {"code": "A"}
    included_workspace = body["included"]["workspaces"][0]
    assert included_workspace["id"] == str(workspace.id)
    assert included_workspace["name"] == "Acme"


def test_get_result_qualifiers_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ResultQualifierFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(RESULT_QUALIFIERS_URL, {"include": ["workspace"]})

    assert response.status_code == 200
    body = response.json()
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_result_qualifiers_include_workspace_does_not_scale_queries_with_count(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    for i in range(5):
        ResultQualifierFactory(workspace=workspace, code=f"A{i}")
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(RESULT_QUALIFIERS_URL, {"include": "workspace"})

    for i in range(5):
        ResultQualifierFactory(workspace=workspace, code=f"B{i}")

    with CaptureQueriesContext(connection) as large:
        client.get(RESULT_QUALIFIERS_URL, {"include": "workspace"})

    assert len(large.captured_queries) == len(small.captured_queries)


# --- create_result_qualifier ---------------------------------------------------------


def test_create_result_qualifier_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        RESULT_QUALIFIERS_URL,
        data=_result_qualifier_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}
    result_qualifier_id = response.json()["id"]

    detail = client.get(_detail_url(result_qualifier_id))
    assert detail.json()["data"]["code"] == "New Qualifier"


def test_create_result_qualifier_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        RESULT_QUALIFIERS_URL,
        data=_result_qualifier_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_result_qualifier_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        RESULT_QUALIFIERS_URL,
        data=_result_qualifier_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_result_qualifier_returns_400_for_duplicate_code_in_workspace(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ResultQualifierFactory(workspace=workspace, code="Duplicate")
    client.force_login(owner)

    response = client.post(
        RESULT_QUALIFIERS_URL,
        data=_result_qualifier_body(workspaceId=str(workspace.id), code="Duplicate"),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_result_qualifier -------------------------------------------------------------


def test_get_result_qualifier_returns_global_qualifier_for_anonymous(client):
    result_qualifier = ResultQualifierFactory(global_=True)

    response = client.get(_detail_url(result_qualifier.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(result_qualifier.id)


def test_get_result_qualifier_returns_404_for_private_workspace_qualifier_when_unrelated(
    client,
):
    workspace = WorkspaceFactory(is_private=True)
    result_qualifier = ResultQualifierFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(result_qualifier.id))

    assert response.status_code == 404


def test_get_result_qualifier_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    result_qualifier = ResultQualifierFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(result_qualifier.id))

    assert response.status_code == 200


def test_get_result_qualifier_returns_404_for_nonexistent_qualifier(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_result_qualifier_included_is_present_but_empty_without_include_param(
    client,
):
    result_qualifier = ResultQualifierFactory(global_=True)

    response = client.get(_detail_url(result_qualifier.id))

    assert response.status_code == 200
    body = response.json()
    assert "included" in body
    assert body["included"] == {}


def test_get_result_qualifier_include_workspace_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    result_qualifier = ResultQualifierFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(result_qualifier.id), {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(result_qualifier.id)
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_result_qualifier_include_rejects_unknown_relation(client):
    result_qualifier = ResultQualifierFactory(global_=True)

    response = client.get(_detail_url(result_qualifier.id), {"include": "bogus"})

    assert response.status_code == 400


def test_get_result_qualifier_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    result_qualifier = ResultQualifierFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(result_qualifier.id), {"include": ["workspace"]})

    assert response.status_code == 200
    body = response.json()
    assert [w["id"] for w in body["included"]["workspaces"]] == [str(workspace.id)]


def test_get_result_qualifier_properties_rejects_unknown_property(client):
    result_qualifier = ResultQualifierFactory(global_=True)

    response = client.get(_detail_url(result_qualifier.id), {"properties": "bogus"})

    assert response.status_code == 400


# --- update_result_qualifier -----------------------------------------------------------


def test_update_result_qualifier_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    result_qualifier = ResultQualifierFactory(workspace=workspace, code="Original Code")
    client.force_login(owner)

    response = client.patch(
        _detail_url(result_qualifier.id),
        data={"code": "Updated Code"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(result_qualifier.id))
    assert detail.json()["data"]["code"] == "Updated Code"


def test_update_result_qualifier_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    result_qualifier = ResultQualifierFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(result_qualifier.id),
        data={"code": "Updated Code"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_result_qualifier -----------------------------------------------------------


def test_delete_result_qualifier_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    result_qualifier = ResultQualifierFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(result_qualifier.id))

    assert response.status_code == 204
    assert client.get(_detail_url(result_qualifier.id)).status_code == 404


def test_delete_result_qualifier_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    result_qualifier = ResultQualifierFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(result_qualifier.id))

    assert response.status_code == 403
