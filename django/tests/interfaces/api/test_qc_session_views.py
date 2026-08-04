from datetime import timedelta

import pytest
from django.utils import timezone

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, ThingFactory
from tests.processing.quality.factories import QCHistoryFactory, QCSessionFactory

pytestmark = pytest.mark.django_db

QC_HISTORIES_URL = "/api/data/quality-control/histories"


def _sessions_url(history_id):
    return f"{QC_HISTORIES_URL}/{history_id}/sessions"


def _detail_url(history_id, session_id):
    return f"{_sessions_url(history_id)}/{session_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Datastream", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_history(workspace, managed_private=False):
    thing = ThingFactory(workspace=workspace)
    managed = DatastreamFactory(thing=thing, private=managed_private)
    source = DatastreamFactory(thing=thing)
    return QCHistoryFactory(managed_datastream=managed, source_datastream=source)


def _iso(dt):
    return dt.isoformat()


def _session_body(**overrides):
    now = timezone.now()
    body = {
        "phenomenonTimeStart": _iso(now - timedelta(days=1)),
        "phenomenonTimeEnd": _iso(now),
    }
    body.update(overrides)
    return body


# --- get_qc_sessions -----------------------------------------------------------------


def test_get_qc_sessions_includes_session_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    session = QCSessionFactory(history=history)
    client.force_login(owner)

    response = client.get(_sessions_url(history.id))

    assert response.status_code == 200
    assert str(session.id) in [s["id"] for s in response.json()]


def test_get_qc_sessions_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    history = _make_history(workspace, managed_private=True)
    QCSessionFactory(history=history)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_sessions_url(history.id))

    assert response.status_code == 404


def test_get_qc_sessions_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    history = _make_history(workspace)

    response = client.get(_sessions_url(history.id))

    assert response.status_code == 401


# --- create_qc_session ---------------------------------------------------------------


def test_create_qc_session_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    client.force_login(owner)

    response = client.post(
        _sessions_url(history.id),
        data=_session_body(),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["status"] == "in_progress"


def test_create_qc_session_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    history = _make_history(workspace)

    response = client.post(
        _sessions_url(history.id),
        data=_session_body(),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_qc_session_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    history = _make_history(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        _sessions_url(history.id),
        data=_session_body(),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_qc_session_returns_400_when_end_before_start(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    now = timezone.now()
    client.force_login(owner)

    response = client.post(
        _sessions_url(history.id),
        data=_session_body(
            phenomenonTimeStart=_iso(now), phenomenonTimeEnd=_iso(now - timedelta(days=1))
        ),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_qc_session_returns_400_when_in_progress_session_already_exists(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    QCSessionFactory(history=history)
    client.force_login(owner)

    response = client.post(
        _sessions_url(history.id),
        data=_session_body(),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_qc_session --------------------------------------------------------------------


def test_get_qc_session_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    session = QCSessionFactory(history=history)
    client.force_login(owner)

    response = client.get(_detail_url(history.id, session.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(session.id)


def test_get_qc_session_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    history = _make_history(workspace, managed_private=True)
    session = QCSessionFactory(history=history)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(history.id, session.id))

    assert response.status_code == 404


def test_get_qc_session_returns_404_for_nonexistent_session(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    client.force_login(owner)

    response = client.get(
        _detail_url(history.id, "00000000-0000-0000-0000-000000000000")
    )

    assert response.status_code == 404


# --- update_qc_session --------------------------------------------------------------------


def test_update_qc_session_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    session = QCSessionFactory(history=history)
    client.force_login(owner)

    response = client.patch(
        _detail_url(history.id, session.id),
        data={"description": "Updated description"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Updated description"


def test_update_qc_session_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    history = _make_history(workspace)
    session = QCSessionFactory(history=history)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(history.id, session.id),
        data={"description": "Updated description"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_update_qc_session_returns_400_for_committed_session(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    session = QCSessionFactory(history=history, committed=True)
    client.force_login(owner)

    response = client.patch(
        _detail_url(history.id, session.id),
        data={"description": "Updated description"},
        content_type="application/json",
    )

    assert response.status_code == 400


# --- delete_qc_session --------------------------------------------------------------------


def test_delete_qc_session_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    session = QCSessionFactory(history=history)
    client.force_login(owner)

    response = client.delete(_detail_url(history.id, session.id))

    assert response.status_code == 204
    assert client.get(_detail_url(history.id, session.id)).status_code == 404


def test_delete_qc_session_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    history = _make_history(workspace)
    session = QCSessionFactory(history=history)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(history.id, session.id))

    assert response.status_code == 403


def test_delete_qc_session_returns_400_for_committed_session(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    session = QCSessionFactory(history=history, committed=True)
    client.force_login(owner)

    response = client.delete(_detail_url(history.id, session.id))

    assert response.status_code == 400


# --- commit_qc_session --------------------------------------------------------------------


def test_commit_qc_session_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    session = QCSessionFactory(history=history)
    client.force_login(owner)

    response = client.post(f"{_detail_url(history.id, session.id)}/commit")

    assert response.status_code == 200
    assert response.json()["status"] == "committed"


def test_commit_qc_session_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    history = _make_history(workspace)
    session = QCSessionFactory(history=history)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(f"{_detail_url(history.id, session.id)}/commit")

    assert response.status_code == 403


def test_commit_qc_session_returns_400_when_already_committed(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    history = _make_history(workspace)
    session = QCSessionFactory(history=history, committed=True)
    client.force_login(owner)

    response = client.post(f"{_detail_url(history.id, session.id)}/commit")

    assert response.status_code == 400
