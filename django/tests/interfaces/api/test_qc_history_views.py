import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory
from tests.processing.quality.factories import QCHistoryFactory

pytestmark = pytest.mark.django_db

QC_HISTORIES_URL = "/api/data/quality-control/histories"


def _detail_url(history_id):
    return f"{QC_HISTORIES_URL}/{history_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Datastream", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_history(workspace, managed_private=False, **kwargs):
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    managed = DatastreamFactory(monitoring_site=monitoring_site, private=managed_private)
    source = DatastreamFactory(monitoring_site=monitoring_site)
    return QCHistoryFactory(managed_datastream=managed, source_datastream=source, **kwargs)


# --- get_qc_histories --------------------------------------------------------------


def test_get_qc_histories_includes_history_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    client.force_login(owner)

    response = client.get(QC_HISTORIES_URL)

    assert response.status_code == 200
    assert str(history.id) in [h["id"] for h in response.json()["data"]]


def test_get_qc_histories_excludes_history_for_outsider(client):
    workspace = WorkspaceFactory()
    _make_history(workspace, managed_private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(QC_HISTORIES_URL)

    assert response.json()["data"] == []


def test_get_qc_histories_returns_401_when_unauthenticated(client):
    response = client.get(QC_HISTORIES_URL)

    assert response.status_code == 401


# --- create_qc_history ---------------------------------------------------------------


def test_create_qc_history_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    managed = DatastreamFactory(monitoring_site=monitoring_site)
    source = DatastreamFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.post(
        QC_HISTORIES_URL,
        data={
            "managedDatastreamId": str(managed.id),
            "sourceDatastreamId": str(source.id),
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    created_id = response.json()["id"]

    detail = client.get(_detail_url(created_id))
    assert detail.json()["data"]["managedDatastreamId"] == str(managed.id)
    assert detail.json()["data"]["sourceDatastreamId"] == str(source.id)


def test_create_qc_history_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    managed = DatastreamFactory(monitoring_site=monitoring_site)
    source = DatastreamFactory(monitoring_site=monitoring_site)

    response = client.post(
        QC_HISTORIES_URL,
        data={
            "managedDatastreamId": str(managed.id),
            "sourceDatastreamId": str(source.id),
        },
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_qc_history_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    managed = DatastreamFactory(monitoring_site=monitoring_site)
    source = DatastreamFactory(monitoring_site=monitoring_site)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        QC_HISTORIES_URL,
        data={
            "managedDatastreamId": str(managed.id),
            "sourceDatastreamId": str(source.id),
        },
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_qc_history_returns_400_when_processing_levels_match(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    managed = DatastreamFactory(monitoring_site=monitoring_site)
    source = DatastreamFactory(monitoring_site=monitoring_site, processing_level=managed.processing_level)
    client.force_login(owner)

    response = client.post(
        QC_HISTORIES_URL,
        data={
            "managedDatastreamId": str(managed.id),
            "sourceDatastreamId": str(source.id),
        },
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_qc_history_returns_400_when_managed_datastream_already_has_history(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    other_source = DatastreamFactory(monitoring_site=history.managed_datastream.monitoring_site)
    client.force_login(owner)

    response = client.post(
        QC_HISTORIES_URL,
        data={
            "managedDatastreamId": str(history.managed_datastream.id),
            "sourceDatastreamId": str(other_source.id),
        },
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_qc_history --------------------------------------------------------------------


def test_get_qc_history_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(history.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(history.id)


def test_get_qc_history_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    history = _make_history(workspace, managed_private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(history.id))

    assert response.status_code == 404


def test_get_qc_history_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    history = _make_history(workspace)

    response = client.get(_detail_url(history.id))

    assert response.status_code == 401


def test_get_qc_history_returns_404_for_nonexistent_history(client):
    owner = UserFactory()
    client.force_login(owner)

    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- delete_qc_history --------------------------------------------------------------------


def test_delete_qc_history_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(history.id))

    assert response.status_code == 204
    assert client.get(_detail_url(history.id)).status_code == 404


def test_delete_qc_history_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    history = _make_history(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(history.id))

    assert response.status_code == 403


# --- include / properties ---------------------------------------------------------


def test_get_qc_history_include_sideloads_both_datastreams(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    client.force_login(owner)

    response = client.get(
        _detail_url(history.id), {"include": "managedDatastream,sourceDatastream"}
    )

    assert response.status_code == 200
    body = response.json()
    assert {row["id"] for row in body["included"]["managedDatastreams"]} == {
        str(history.managed_datastream_id)
    }
    assert {row["id"] for row in body["included"]["sourceDatastreams"]} == {
        str(history.source_datastream_id)
    }


def test_get_qc_history_without_include_omits_included_bucket(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(history.id))

    assert response.status_code == 200
    assert not response.json().get("included")


def test_get_qc_histories_include_does_not_scale_queries_with_history_count(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    for _ in range(5):
        _make_history(workspace)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(QC_HISTORIES_URL, {"include": "managedDatastream,sourceDatastream"})

    for _ in range(5):
        _make_history(workspace)

    with CaptureQueriesContext(connection) as large:
        client.get(QC_HISTORIES_URL, {"include": "managedDatastream,sourceDatastream"})

    assert len(large.captured_queries) == len(small.captured_queries)


def test_get_qc_histories_properties_filters_response_fields(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    _make_history(workspace)
    client.force_login(owner)

    response = client.get(QC_HISTORIES_URL, {"properties": "id,createdAt"})

    assert response.status_code == 200
    row = response.json()["data"][0]
    assert set(row.keys()) == {"id", "createdAt"}
