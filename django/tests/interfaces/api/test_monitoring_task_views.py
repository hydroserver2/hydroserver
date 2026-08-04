from unittest.mock import patch

import pytest

from processing.orchestration.models import TaskRun
from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import ThingFactory
from tests.processing.monitoring.factories import MonitoringTaskFactory

pytestmark = pytest.mark.django_db

MONITORING_TASKS_URL = "/api/data/monitoring/tasks"


def _detail_url(task_id):
    return f"{MONITORING_TASKS_URL}/{task_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="MonitoringTask", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_monitoring_task(workspace, **kwargs):
    return MonitoringTaskFactory(thing=ThingFactory(workspace=workspace), **kwargs)


def _monitoring_task_body(thing_id, **overrides):
    body = {
        "name": "New Monitoring Task",
        "thingId": str(thing_id),
    }
    body.update(overrides)
    return body


# --- get_monitoring_tasks -----------------------------------------------------------


def test_get_monitoring_tasks_includes_task_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_monitoring_task(workspace)
    client.force_login(owner)

    response = client.get(MONITORING_TASKS_URL)

    assert response.status_code == 200
    assert str(task.id) in [t["id"] for t in response.json()]


def test_get_monitoring_tasks_excludes_task_for_outsider(client):
    workspace = WorkspaceFactory()
    _make_monitoring_task(workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(MONITORING_TASKS_URL)

    assert response.json() == []


def test_get_monitoring_tasks_returns_401_when_unauthenticated(client):
    response = client.get(MONITORING_TASKS_URL)

    assert response.status_code == 401


# --- create_monitoring_task -----------------------------------------------------------


def test_create_monitoring_task_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = ThingFactory(workspace=workspace)
    client.force_login(owner)

    response = client.post(
        MONITORING_TASKS_URL,
        data=_monitoring_task_body(thing.id),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["name"] == "New Monitoring Task"


def test_create_monitoring_task_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    thing = ThingFactory(workspace=workspace)

    response = client.post(
        MONITORING_TASKS_URL,
        data=_monitoring_task_body(thing.id),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_monitoring_task_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    thing = ThingFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        MONITORING_TASKS_URL,
        data=_monitoring_task_body(thing.id),
        content_type="application/json",
    )

    assert response.status_code == 403


# --- get_monitoring_task ----------------------------------------------------------------


def test_get_monitoring_task_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_monitoring_task(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(task.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(task.id)


def test_get_monitoring_task_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    task = _make_monitoring_task(workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(task.id))

    assert response.status_code == 404


def test_get_monitoring_task_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    task = _make_monitoring_task(workspace)

    response = client.get(_detail_url(task.id))

    assert response.status_code == 401


def test_get_monitoring_task_returns_404_for_nonexistent_task(client):
    owner = UserFactory()
    client.force_login(owner)

    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- update_monitoring_task ----------------------------------------------------------------


def test_update_monitoring_task_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_monitoring_task(workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(task.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_update_monitoring_task_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task = _make_monitoring_task(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(task.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_monitoring_task ----------------------------------------------------------------


def test_delete_monitoring_task_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_monitoring_task(workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(task.id))

    assert response.status_code == 204
    assert client.get(_detail_url(task.id)).status_code == 404


def test_delete_monitoring_task_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task = _make_monitoring_task(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(task.id))

    assert response.status_code == 403


# --- trigger_monitoring_task (basic verification, no real rule execution) ------------------


def test_trigger_monitoring_task_creates_pending_run_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_monitoring_task(workspace)
    client.force_login(owner)

    with patch("processing.monitoring.tasks.run_monitoring_task.apply_async") as mock_apply_async:
        response = client.post(f"{_detail_url(task.id)}/trigger")

    assert response.status_code == 202
    assert response.json()["status"] == "PENDING"
    mock_apply_async.assert_called_once()
    assert TaskRun.objects.filter(task=task, status="PENDING").exists()


def test_trigger_monitoring_task_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task = _make_monitoring_task(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    with patch("processing.monitoring.tasks.run_monitoring_task.apply_async") as mock_apply_async:
        response = client.post(f"{_detail_url(task.id)}/trigger")

    assert response.status_code == 403
    mock_apply_async.assert_not_called()


# --- get_monitoring_task_runs / get_monitoring_task_run (basic verification only) ----------


def test_get_monitoring_task_runs_returns_runs_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_monitoring_task(workspace)
    run = TaskRun.objects.create(task=task, status="SUCCESS")
    client.force_login(owner)

    response = client.get(f"{_detail_url(task.id)}/runs")

    assert response.status_code == 200
    assert str(run.id) in [r["id"] for r in response.json()]


def test_get_monitoring_task_run_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_monitoring_task(workspace)
    run = TaskRun.objects.create(task=task, status="SUCCESS")
    client.force_login(owner)

    response = client.get(f"{_detail_url(task.id)}/runs/{run.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(run.id)
