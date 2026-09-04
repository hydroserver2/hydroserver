import pytest

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
    assert str(result_qualifier.id) in [r["id"] for r in response.json()]


def test_get_result_qualifiers_excludes_private_workspace_qualifiers_for_outsider(
    client,
):
    workspace = WorkspaceFactory(is_private=True)
    ResultQualifierFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(RESULT_QUALIFIERS_URL)

    assert response.json() == []


def test_get_result_qualifiers_includes_workspace_qualifiers_for_workspace_owner(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    result_qualifier = ResultQualifierFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(RESULT_QUALIFIERS_URL)

    assert response.status_code == 200
    assert str(result_qualifier.id) in [r["id"] for r in response.json()]


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
    assert response.json()["code"] == "New Qualifier"


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


def test_create_result_qualifier_returns_422_for_duplicate_code_in_workspace(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    ResultQualifierFactory(workspace=workspace, code="Duplicate")
    client.force_login(owner)

    response = client.post(
        RESULT_QUALIFIERS_URL,
        data=_result_qualifier_body(workspaceId=str(workspace.id), code="Duplicate"),
        content_type="application/json",
    )

    assert response.status_code == 422


# --- get_result_qualifier -------------------------------------------------------------


def test_get_result_qualifier_returns_global_qualifier_for_anonymous(client):
    result_qualifier = ResultQualifierFactory(global_=True)

    response = client.get(_detail_url(result_qualifier.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(result_qualifier.id)


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

    assert response.status_code == 200
    assert response.json()["code"] == "Updated Code"


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
