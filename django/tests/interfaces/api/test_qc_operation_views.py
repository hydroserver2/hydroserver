import pytest

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory
from tests.processing.quality.factories import (
    QCHistoryFactory,
    QCOperationFactory,
    QCSessionFactory,
)

pytestmark = pytest.mark.django_db

QC_HISTORIES_URL = "/api/data/quality-control/histories"


def _operations_url(history_id, session_id):
    return f"{QC_HISTORIES_URL}/{history_id}/sessions/{session_id}/operations"


def _detail_url(history_id, session_id, operation_id):
    return f"{_operations_url(history_id, session_id)}/{operation_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Datastream", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_session(workspace, managed_private=False, **kwargs):
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    managed = DatastreamFactory(monitoring_site=monitoring_site, private=managed_private)
    source = DatastreamFactory(monitoring_site=monitoring_site)
    history = QCHistoryFactory(managed_datastream=managed, source_datastream=source)
    return QCSessionFactory(history=history, **kwargs)


def _operation_body(**overrides):
    body = {
        "operationType": "SELECTION",
        "order": 0,
        "arguments": {"start": 0, "end": 10},
    }
    body.update(overrides)
    return body


# --- get_qc_operations -----------------------------------------------------------------


def test_get_qc_operations_includes_operation_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    session = _make_session(workspace)
    operation = QCOperationFactory(session=session)
    client.force_login(owner)

    response = client.get(_operations_url(session.history_id, session.id))

    assert response.status_code == 200
    assert str(operation.id) in [o["id"] for o in response.json()]


def test_get_qc_operations_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    session = _make_session(workspace, managed_private=True)
    QCOperationFactory(session=session)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_operations_url(session.history_id, session.id))

    assert response.status_code == 404


def test_get_qc_operations_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    session = _make_session(workspace)

    response = client.get(_operations_url(session.history_id, session.id))

    assert response.status_code == 401


# --- create_qc_operations ---------------------------------------------------------------


def test_create_qc_operations_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    session = _make_session(workspace)
    client.force_login(owner)

    response = client.post(
        _operations_url(session.history_id, session.id),
        data=[_operation_body()],
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()[0]["operationType"] == "SELECTION"


def test_create_qc_operations_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    session = _make_session(workspace)

    response = client.post(
        _operations_url(session.history_id, session.id),
        data=[_operation_body()],
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_qc_operations_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    session = _make_session(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        _operations_url(session.history_id, session.id),
        data=[_operation_body()],
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_qc_operations_returns_400_for_committed_session(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    session = _make_session(workspace, committed=True)
    client.force_login(owner)

    response = client.post(
        _operations_url(session.history_id, session.id),
        data=[_operation_body()],
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_qc_operation --------------------------------------------------------------------


def test_get_qc_operation_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    session = _make_session(workspace)
    operation = QCOperationFactory(session=session)
    client.force_login(owner)

    response = client.get(_detail_url(session.history_id, session.id, operation.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(operation.id)


def test_get_qc_operation_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    session = _make_session(workspace, managed_private=True)
    operation = QCOperationFactory(session=session)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(session.history_id, session.id, operation.id))

    assert response.status_code == 404


def test_get_qc_operation_returns_404_for_nonexistent_operation(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    session = _make_session(workspace)
    client.force_login(owner)

    response = client.get(
        _detail_url(session.history_id, session.id, "00000000-0000-0000-0000-000000000000")
    )

    assert response.status_code == 404


# --- update_qc_operation --------------------------------------------------------------------


def test_update_qc_operation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    session = _make_session(workspace)
    operation = QCOperationFactory(session=session, comment="Original comment")
    client.force_login(owner)

    response = client.patch(
        _detail_url(session.history_id, session.id, operation.id),
        data={"comment": "Updated comment"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["comment"] == "Updated comment"


def test_update_qc_operation_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    session = _make_session(workspace)
    operation = QCOperationFactory(session=session)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(session.history_id, session.id, operation.id),
        data={"comment": "Updated comment"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_update_qc_operation_returns_400_for_committed_session(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    session = _make_session(workspace, committed=True)
    operation = QCOperationFactory(session=session)
    client.force_login(owner)

    response = client.patch(
        _detail_url(session.history_id, session.id, operation.id),
        data={"comment": "Updated comment"},
        content_type="application/json",
    )

    assert response.status_code == 400


# --- delete_qc_operation --------------------------------------------------------------------


def test_delete_qc_operation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    session = _make_session(workspace)
    operation = QCOperationFactory(session=session)
    client.force_login(owner)

    response = client.delete(_detail_url(session.history_id, session.id, operation.id))

    assert response.status_code == 204
    assert (
        client.get(_detail_url(session.history_id, session.id, operation.id)).status_code
        == 404
    )


def test_delete_qc_operation_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    session = _make_session(workspace)
    operation = QCOperationFactory(session=session)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(session.history_id, session.id, operation.id))

    assert response.status_code == 403


def test_delete_qc_operation_returns_400_for_committed_session(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    session = _make_session(workspace, committed=True)
    operation = QCOperationFactory(session=session)
    client.force_login(owner)

    response = client.delete(_detail_url(session.history_id, session.id, operation.id))

    assert response.status_code == 400
