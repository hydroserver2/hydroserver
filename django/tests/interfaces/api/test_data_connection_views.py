import uuid

import pytest

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.processing.etl.factories import DataConnectionFactory, PayloadFactory

pytestmark = pytest.mark.django_db

DATA_CONNECTIONS_URL = "/api/data/etl/data-connections"


def _detail_url(data_connection_id):
    return f"{DATA_CONNECTIONS_URL}/{data_connection_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="DataConnection", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_data_connection(workspace, json=False, **kwargs):
    data_connection = DataConnectionFactory(workspace=workspace, **kwargs)
    PayloadFactory(data_connection=data_connection, json=json)
    return data_connection


def _csv_payload_body(**overrides):
    body = {
        "type": "CSV",
        "timestampKey": "timestamp",
        "headerRow": 1,
        "dataStartRow": 2,
        "delimiter": ",",
    }
    body.update(overrides)
    return body


def _json_payload_body(**overrides):
    body = {
        "type": "JSON",
        "timestampKey": "timestamp",
        "jmespath": "observations",
    }
    body.update(overrides)
    return body


def _data_connection_body(workspace_id, payload=None, **overrides):
    body = {
        "name": "New Data Connection",
        "sourceUrl": "https://example.com/data.csv",
        "workspaceId": str(workspace_id),
        "payload": payload or _csv_payload_body(),
        "placeholderVariables": [],
    }
    body.update(overrides)
    return body


# --- get_data_connections ----------------------------------------------------------


def test_get_data_connections_includes_connection_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    data_connection = _make_data_connection(workspace)
    client.force_login(owner)

    response = client.get(DATA_CONNECTIONS_URL)

    assert response.status_code == 200
    assert str(data_connection.id) in [d["id"] for d in response.json()]


def test_get_data_connections_excludes_connection_for_outsider(client):
    workspace = WorkspaceFactory()
    _make_data_connection(workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(DATA_CONNECTIONS_URL)

    assert response.json() == []


def test_get_data_connections_returns_401_when_unauthenticated(client):
    response = client.get(DATA_CONNECTIONS_URL)

    assert response.status_code == 401


# --- create_data_connection ----------------------------------------------------------


def test_create_data_connection_succeeds_with_csv_payload_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        DATA_CONNECTIONS_URL,
        data=_data_connection_body(workspace.id, payload=_csv_payload_body()),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["payload"]["type"] == "CSV"


def test_create_data_connection_succeeds_with_json_payload_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        DATA_CONNECTIONS_URL,
        data=_data_connection_body(workspace.id, payload=_json_payload_body()),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["payload"]["type"] == "JSON"


def test_create_data_connection_returns_404_for_nonexistent_workspace(client):
    owner = UserFactory()
    client.force_login(owner)

    response = client.post(
        DATA_CONNECTIONS_URL,
        data=_data_connection_body(uuid.uuid4()),
        content_type="application/json",
    )

    assert response.status_code == 404


def test_create_data_connection_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        DATA_CONNECTIONS_URL,
        data=_data_connection_body(workspace.id),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_data_connection_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        DATA_CONNECTIONS_URL,
        data=_data_connection_body(workspace.id),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_data_connection_returns_422_when_csv_payload_missing_required_fields(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        DATA_CONNECTIONS_URL,
        data=_data_connection_body(
            workspace.id, payload={"type": "CSV", "timestampKey": "timestamp"}
        ),
        content_type="application/json",
    )

    assert response.status_code == 422


def test_create_data_connection_returns_422_when_json_payload_missing_jmespath(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        DATA_CONNECTIONS_URL,
        data=_data_connection_body(
            workspace.id, payload={"type": "JSON", "timestampKey": "timestamp"}
        ),
        content_type="application/json",
    )

    assert response.status_code == 422


def test_create_data_connection_returns_422_for_invalid_jmespath_expression(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        DATA_CONNECTIONS_URL,
        data=_data_connection_body(
            workspace.id, payload=_json_payload_body(jmespath="[invalid(")
        ),
        content_type="application/json",
    )

    assert response.status_code == 422


def test_create_data_connection_returns_422_for_unknown_iana_timezone(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        DATA_CONNECTIONS_URL,
        data=_data_connection_body(
            workspace.id, timezoneType="iana", timezone="Not/Real"
        ),
        content_type="application/json",
    )

    assert response.status_code == 422


def test_create_data_connection_returns_422_for_malformed_offset_timezone(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        DATA_CONNECTIONS_URL,
        data=_data_connection_body(
            workspace.id, timezoneType="offset", timezone="not-an-offset"
        ),
        content_type="application/json",
    )

    assert response.status_code == 422


def test_create_data_connection_with_placeholder_variables_succeeds(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        DATA_CONNECTIONS_URL,
        data=_data_connection_body(
            workspace.id,
            placeholderVariables=[{"name": "site_code", "type": "per_task"}],
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["placeholderVariables"] == [
        {"name": "site_code", "type": "per_task", "timestampFormat": None}
    ]


def test_create_data_connection_returns_422_for_timestamp_format_on_disallowed_variable_type(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        DATA_CONNECTIONS_URL,
        data=_data_connection_body(
            workspace.id,
            placeholderVariables=[
                {
                    "name": "site_code",
                    "type": "per_task",
                    "timestampFormat": "%Y-%m-%d",
                }
            ],
        ),
        content_type="application/json",
    )

    assert response.status_code == 422


# --- get_data_connection ----------------------------------------------------------------


def test_get_data_connection_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    data_connection = _make_data_connection(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(data_connection.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(data_connection.id)


def test_get_data_connection_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    data_connection = _make_data_connection(workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(data_connection.id))

    assert response.status_code == 404


def test_get_data_connection_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    data_connection = _make_data_connection(workspace)

    response = client.get(_detail_url(data_connection.id))

    assert response.status_code == 401


def test_get_data_connection_returns_404_for_nonexistent_connection(client):
    owner = UserFactory()
    client.force_login(owner)

    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- update_data_connection ----------------------------------------------------------------


def test_update_data_connection_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    data_connection = _make_data_connection(workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(data_connection.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_update_data_connection_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    data_connection = _make_data_connection(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(data_connection.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_data_connection ----------------------------------------------------------------


def test_delete_data_connection_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    data_connection = _make_data_connection(workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(data_connection.id))

    assert response.status_code == 204
    assert client.get(_detail_url(data_connection.id)).status_code == 404


def test_delete_data_connection_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    data_connection = _make_data_connection(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(data_connection.id))

    assert response.status_code == 403
