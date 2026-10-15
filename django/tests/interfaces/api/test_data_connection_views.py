import uuid
from datetime import datetime

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

DATA_CONNECTIONS_URL = "/api/ogc/collections/etl-data-connections/items"


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


def _ingestion_window():
    return {
        "start": {
            "anchor": "latest_observation_timestamp",
            "lookback": 2,
            "lookbackUnits": "hours",
            "timestamp": None,
        },
        "end": {
            "anchor": "fixed_timestamp",
            "lookback": None,
            "lookbackUnits": None,
            "timestamp": "2026-01-01T00:00:00+00:00",
        },
    }


@pytest.fixture(params=[False, True], ids=["CSV", "JSON"])
def windowed_data_connection(client, request):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    data_connection = DataConnectionFactory(workspace=workspace)
    PayloadFactory(
        data_connection=data_connection,
        json=request.param,
        data_ingestion_window_start_anchor="latest_observation_timestamp",
        data_ingestion_window_start_lookback=2,
        data_ingestion_window_start_lookback_unit="hours",
        data_ingestion_window_end_anchor="fixed_timestamp",
        data_ingestion_window_end_timestamp=datetime.fromisoformat("2026-01-01T00:00:00+00:00"),
    )
    client.force_login(owner)
    return data_connection


# --- get_data_connections ----------------------------------------------------------


def test_get_data_connections_includes_connection_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    data_connection = _make_data_connection(workspace)
    client.force_login(owner)

    response = client.get(DATA_CONNECTIONS_URL)

    assert response.status_code == 200
    assert str(data_connection.id) in [d["id"] for d in response.json()["data"]]


def test_get_data_connections_excludes_connection_for_outsider(client):
    workspace = WorkspaceFactory()
    _make_data_connection(workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(DATA_CONNECTIONS_URL)

    assert response.json()["data"] == []


def test_get_data_connections_returns_401_when_unauthenticated(client):
    response = client.get(DATA_CONNECTIONS_URL)

    assert response.status_code == 401


# --- full-text search (q) ------------------------------------------------------------


def test_get_data_connections_q_matches_name(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    match = _make_data_connection(workspace, name="Zephyr Gauge Feed")
    _make_data_connection(workspace, name="Unrelated Feed")
    client.force_login(owner)

    response = client.get(DATA_CONNECTIONS_URL, {"q": "Zephyr"})

    assert response.status_code == 200
    assert {d["id"] for d in response.json()["data"]} == {str(match.id)}


def test_get_data_connections_q_matches_timezone_type_field(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    match = _make_data_connection(
        workspace, name="Site A", timezone_type="iana", timezone="America/Denver"
    )
    _make_data_connection(workspace, name="Site B", timezone_type=None, timezone=None)
    client.force_login(owner)

    response = client.get(DATA_CONNECTIONS_URL, {"q": "iana"})

    assert {d["id"] for d in response.json()["data"]} == {str(match.id)}


def test_get_data_connections_q_orders_by_relevance_by_default(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    name_match = _make_data_connection(workspace, name="Willowbrook Feed")
    description_match = _make_data_connection(
        workspace, name="Other Feed", description="Willowbrook mentioned here"
    )
    client.force_login(owner)

    response = client.get(DATA_CONNECTIONS_URL, {"q": "Willowbrook"})

    ids = [d["id"] for d in response.json()["data"]]
    assert ids == [str(name_match.id), str(description_match.id)]


def test_get_data_connections_include_workspace_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    data_connection = _make_data_connection(workspace)
    client.force_login(owner)

    response = client.get(DATA_CONNECTIONS_URL, {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    row = next(d for d in body["data"] if d["id"] == str(data_connection.id))
    assert row["workspaceId"] == str(workspace.id)
    assert {w["id"] for w in body["included"]["workspaces"]} == {str(workspace.id)}


def test_get_data_connections_without_include_omits_included_bucket(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    _make_data_connection(workspace)
    client.force_login(owner)

    response = client.get(DATA_CONNECTIONS_URL)

    assert response.status_code == 200
    assert not response.json().get("included")


def test_get_data_connections_include_rejects_unknown_relation(client):
    owner = UserFactory()
    client.force_login(owner)

    response = client.get(DATA_CONNECTIONS_URL, {"include": "bogus"})

    assert response.status_code == 400


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
    assert "id" in response.json()


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
    assert "id" in response.json()


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


def test_create_data_connection_returns_400_when_csv_payload_missing_required_fields(
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

    assert response.status_code == 400


def test_create_data_connection_returns_400_when_json_payload_missing_jmespath(client):
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

    assert response.status_code == 400


def test_create_data_connection_returns_400_for_invalid_jmespath_expression(client):
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

    assert response.status_code == 400


def test_create_data_connection_returns_400_for_unknown_iana_timezone(client):
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

    assert response.status_code == 400


def test_create_data_connection_returns_400_for_malformed_offset_timezone(client):
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

    assert response.status_code == 400


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
    created_id = response.json()["id"]

    detail_response = client.get(_detail_url(created_id))
    assert detail_response.json()["data"]["placeholderVariables"] == [
        {"name": "site_code", "type": "per_task", "timestampFormat": None}
    ]


def test_create_data_connection_returns_400_for_timestamp_format_on_disallowed_variable_type(
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

    assert response.status_code == 400


@pytest.mark.parametrize(
    "payload_body", [_csv_payload_body, _json_payload_body], ids=["CSV", "JSON"]
)
@pytest.mark.parametrize("window", [None, _ingestion_window()], ids=["null", "configured"])
def test_create_data_connection_persists_ingestion_window(client, payload_body, window):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        DATA_CONNECTIONS_URL,
        data=_data_connection_body(
            workspace.id, payload=payload_body(dataIngestionWindow=window)
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    detail = client.get(_detail_url(response.json()["id"]))
    assert detail.json()["data"]["payload"]["dataIngestionWindow"] == window


# --- get_data_connection ----------------------------------------------------------------


def test_get_data_connection_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    data_connection = _make_data_connection(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(data_connection.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(data_connection.id)


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

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(data_connection.id))
    assert detail.json()["data"]["name"] == "Updated Name"


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


@pytest.mark.parametrize("is_json", [False, True], ids=["CSV", "JSON"])
def test_update_data_connection_accepts_fetched_connection_with_null_window(client, is_json):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    data_connection = _make_data_connection(workspace, json=is_json)
    client.force_login(owner)
    url = _detail_url(data_connection.id)
    body = client.get(url).json()["data"]
    assert body["payload"]["dataIngestionWindow"] is None
    body.update(
        name="Updated Name",
        sourceUrl="https://example.com/updated",
        authHeaderName="Authorization",
        authHeaderValue="Bearer updated",
    )
    body["payload"]["timestampKey"] = "updated_timestamp"

    response = client.patch(url, data=body, content_type="application/json")

    assert response.status_code == 204
    detail = client.get(url).json()["data"]
    for field in ("name", "sourceUrl", "authHeaderName", "authHeaderValue", "payload"):
        assert detail[field] == body[field]


def test_update_data_connection_accepts_fetched_connection_with_window(client, windowed_data_connection):
    url = _detail_url(windowed_data_connection.id)
    body = client.get(url).json()["data"]
    assert body["payload"]["dataIngestionWindow"] == _ingestion_window()
    body["name"] = "Renamed connection"

    response = client.patch(url, data=body, content_type="application/json")

    assert response.status_code == 204
    detail = client.get(url).json()["data"]
    assert detail["name"] == "Renamed connection"
    assert detail["payload"]["dataIngestionWindow"] == _ingestion_window()


def test_update_data_connection_can_reenable_window(client, windowed_data_connection):
    url = _detail_url(windowed_data_connection.id)
    for window in (None, _ingestion_window()):
        response = client.patch(
            url,
            data={"payload": {"dataIngestionWindow": window}},
            content_type="application/json",
        )

        assert response.status_code == 204
        assert client.get(url).json()["data"]["payload"]["dataIngestionWindow"] == window


@pytest.mark.parametrize("patch", [{"name": "Renamed"}, {"payload": {"timestampKey": "updated"}}])
def test_update_data_connection_preserves_omitted_window(client, windowed_data_connection, patch):
    url = _detail_url(windowed_data_connection.id)

    response = client.patch(url, data=patch, content_type="application/json")

    assert response.status_code == 204
    assert client.get(url).json()["data"]["payload"]["dataIngestionWindow"] == _ingestion_window()


@pytest.mark.parametrize(
    ("window_patch", "expected"),
    [
        (None, None),
        ({}, _ingestion_window()),
        ({"start": None}, {**_ingestion_window(), "start": None}),
        ({"end": None}, {**_ingestion_window(), "end": None}),
        ({"start": {}}, _ingestion_window()),
        (
            {"start": {"lookback": 3}},
            {**_ingestion_window(), "start": {**_ingestion_window()["start"], "lookback": 3}},
        ),
        (
            {"start": {"lookback": 0, "lookbackUnits": "days"}},
            {
                **_ingestion_window(),
                "start": {**_ingestion_window()["start"], "lookback": 0, "lookbackUnits": "days"},
            },
        ),
        (
            {"start": {"lookback": None, "lookbackUnits": None}},
            {
                **_ingestion_window(),
                "start": {**_ingestion_window()["start"], "lookback": None, "lookbackUnits": None},
            },
        ),
        (
            {"end": {"anchor": "run_time", "timestamp": None}},
            {**_ingestion_window(), "end": {**_ingestion_window()["end"], "anchor": "run_time", "timestamp": None}},
        ),
    ],
    ids=[
        "clear-window", "empty-window", "clear-start", "clear-end", "empty-start",
        "lookback-only", "zero-lookback", "clear-lookback", "change-anchor",
    ],
)
def test_update_data_connection_patches_ingestion_window(
    client, windowed_data_connection, window_patch, expected
):
    url = _detail_url(windowed_data_connection.id)

    response = client.patch(
        url,
        data={"payload": {"dataIngestionWindow": window_patch}},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert client.get(url).json()["data"]["payload"]["dataIngestionWindow"] == expected
    if expected is None:
        payload = windowed_data_connection.payload
        payload.refresh_from_db()
        for side in ("start", "end"):
            for suffix in ("anchor", "lookback", "lookback_unit", "timestamp"):
                assert getattr(payload, f"data_ingestion_window_{side}_{suffix}") is None


def test_update_data_connection_preserves_window_when_switching_payload_type(client, windowed_data_connection):
    url = _detail_url(windowed_data_connection.id)
    payload = (
        _json_payload_body() if windowed_data_connection.payload.payload_type == "CSV"
        else _csv_payload_body()
    )

    response = client.patch(url, data={"payload": payload}, content_type="application/json")

    assert response.status_code == 204
    detail = client.get(url).json()["data"]["payload"]
    assert detail["type"] == payload["type"]
    assert detail["dataIngestionWindow"] == _ingestion_window()


@pytest.mark.parametrize(
    "window_patch",
    [{"end": {"timestamp": None}}, {"start": {"lookbackUnits": None}}, {"start": {"anchor": None}}],
)
def test_update_data_connection_validates_merged_window(client, windowed_data_connection, window_patch):
    url = _detail_url(windowed_data_connection.id)
    original = client.get(url).json()["data"]

    response = client.patch(
        url,
        data={"name": "Rejected Name", "payload": {"dataIngestionWindow": window_patch}},
        content_type="application/json",
    )

    assert response.status_code == 400
    detail = client.get(url).json()["data"]
    assert detail["name"] == original["name"]
    assert detail["payload"]["dataIngestionWindow"] == original["payload"]["dataIngestionWindow"]


@pytest.mark.parametrize(
    "boundary",
    [
        {"anchor": "invalid"},
        {"anchor": "fixed_timestamp"},
        {"anchor": "fixed_timestamp", "timestamp": "invalid"},
        {"anchor": "run_time", "lookback": -1, "lookbackUnits": "hours"},
        {"anchor": "run_time", "lookback": 1, "lookbackUnits": "weeks"},
        {"anchor": "run_time", "lookback": 1},
        {"anchor": "run_time", "lookbackUnits": "hours"},
        {"lookback": 1, "lookbackUnits": "hours"},
    ],
)
@pytest.mark.parametrize("method", ["post", "patch"])
def test_data_connection_rejects_invalid_ingestion_window(client, boundary, method):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)
    payload = _csv_payload_body(dataIngestionWindow={"start": boundary})
    if method == "post":
        url = DATA_CONNECTIONS_URL
        body = _data_connection_body(workspace.id, payload=payload)
    else:
        data_connection = _make_data_connection(workspace, name="Original Name")
        url = _detail_url(data_connection.id)
        body = {"name": "Rejected Name", "payload": payload}

    response = getattr(client, method)(url, data=body, content_type="application/json")

    assert response.status_code == 400
    if method == "post":
        assert not workspace.data_connections.exists()
    else:
        data_connection.refresh_from_db()
        data_connection.payload.refresh_from_db()
        assert data_connection.name == "Original Name"
        assert data_connection.payload.data_ingestion_window_start_anchor is None


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
