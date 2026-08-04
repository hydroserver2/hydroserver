import pytest

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, ThingFactory
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
    thing = ThingFactory(workspace=workspace)
    managed = DatastreamFactory(thing=thing, private=managed_private)
    source = DatastreamFactory(thing=thing)
    return QCHistoryFactory(managed_datastream=managed, source_datastream=source, **kwargs)


# --- get_qc_histories --------------------------------------------------------------


def test_get_qc_histories_includes_history_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    client.force_login(owner)

    response = client.get(QC_HISTORIES_URL)

    assert response.status_code == 200
    assert str(history.id) in [h["id"] for h in response.json()]


def test_get_qc_histories_excludes_history_for_outsider(client):
    workspace = WorkspaceFactory()
    _make_history(workspace, managed_private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(QC_HISTORIES_URL)

    assert response.json() == []


def test_get_qc_histories_returns_401_when_unauthenticated(client):
    response = client.get(QC_HISTORIES_URL)

    assert response.status_code == 401


# --- create_qc_history ---------------------------------------------------------------


def test_create_qc_history_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = ThingFactory(workspace=workspace)
    managed = DatastreamFactory(thing=thing)
    source = DatastreamFactory(thing=thing)
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
    assert response.json()["managedDatastream"]["id"] == str(managed.id)


def test_create_qc_history_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    thing = ThingFactory(workspace=workspace)
    managed = DatastreamFactory(thing=thing)
    source = DatastreamFactory(thing=thing)

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
    thing = ThingFactory(workspace=workspace)
    managed = DatastreamFactory(thing=thing)
    source = DatastreamFactory(thing=thing)
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
    thing = ThingFactory(workspace=workspace)
    managed = DatastreamFactory(thing=thing)
    source = DatastreamFactory(thing=thing, processing_level=managed.processing_level)
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
    other_source = DatastreamFactory(thing=history.managed_datastream.thing)
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
    assert response.json()["id"] == str(history.id)


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
