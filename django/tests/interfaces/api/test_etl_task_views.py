from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from processing.orchestration.models import TaskRun
from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.processing.etl.factories import DataConnectionFactory, EtlTaskFactory, PayloadFactory

pytestmark = pytest.mark.django_db

ETL_TASKS_URL = "/api/data/etl/tasks"


def _detail_url(task_id):
    return f"{ETL_TASKS_URL}/{task_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="EtlTask", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_etl_task(workspace, **kwargs):
    data_connection = DataConnectionFactory(workspace=workspace)
    PayloadFactory(data_connection=data_connection)
    return EtlTaskFactory(data_connection=data_connection, **kwargs)


def _etl_task_body(data_connection_id, **overrides):
    body = {
        "name": "New ETL Task",
        "dataConnectionId": str(data_connection_id),
    }
    body.update(overrides)
    return body


# --- get_etl_tasks -----------------------------------------------------------------


def test_get_etl_tasks_includes_task_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_etl_task(workspace)
    client.force_login(owner)

    response = client.get(ETL_TASKS_URL)

    assert response.status_code == 200
    assert str(task.id) in [t["id"] for t in response.json()["data"]]


def test_get_etl_tasks_excludes_task_for_outsider(client):
    workspace = WorkspaceFactory()
    _make_etl_task(workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(ETL_TASKS_URL)

    assert response.json()["data"] == []


def test_get_etl_tasks_include_data_connection_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_etl_task(workspace)
    client.force_login(owner)

    response = client.get(ETL_TASKS_URL, {"include": "dataConnection"})

    assert response.status_code == 200
    body = response.json()
    row = next(t for t in body["data"] if t["id"] == str(task.id))
    assert row["dataConnectionId"] == str(task.data_connection_id)
    assert {dc["id"] for dc in body["included"]["dataConnections"]} == {
        str(task.data_connection_id)
    }


def test_get_etl_tasks_include_data_connection_does_not_scale_queries(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    _make_etl_task(workspace)
    _make_etl_task(workspace)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(ETL_TASKS_URL, {"include": "dataConnection"})

    for _ in range(10):
        _make_etl_task(workspace)

    with CaptureQueriesContext(connection) as large:
        client.get(ETL_TASKS_URL, {"include": "dataConnection"})

    assert len(large.captured_queries) == len(small.captured_queries)


def test_get_etl_tasks_returns_401_when_unauthenticated(client):
    response = client.get(ETL_TASKS_URL)

    assert response.status_code == 401


# --- create_etl_task -----------------------------------------------------------------


def test_create_etl_task_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    data_connection = DataConnectionFactory(workspace=workspace)
    client.force_login(owner)

    response = client.post(
        ETL_TASKS_URL,
        data=_etl_task_body(data_connection.id),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}
    detail = client.get(_detail_url(response.json()["id"]))
    assert detail.json()["data"]["name"] == "New ETL Task"


def test_create_etl_task_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    data_connection = DataConnectionFactory(workspace=workspace)

    response = client.post(
        ETL_TASKS_URL,
        data=_etl_task_body(data_connection.id),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_etl_task_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    data_connection = DataConnectionFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        ETL_TASKS_URL,
        data=_etl_task_body(data_connection.id),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_etl_task_returns_400_for_malformed_crontab(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    data_connection = DataConnectionFactory(workspace=workspace)
    client.force_login(owner)

    response = client.post(
        ETL_TASKS_URL,
        data=_etl_task_body(data_connection.id, schedule={"crontab": "* * *"}),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_etl_task_with_valid_crontab_returns_schedule_in_response(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    data_connection = DataConnectionFactory(workspace=workspace)
    client.force_login(owner)

    response = client.post(
        ETL_TASKS_URL,
        data=_etl_task_body(data_connection.id, schedule={"crontab": "0 5 * * *"}),
        content_type="application/json",
    )

    assert response.status_code == 201
    detail = client.get(_detail_url(response.json()["id"]))
    assert detail.json()["data"]["schedule"]["crontab"] == "0 5 * * *"


# --- get_etl_task ----------------------------------------------------------------------


def test_get_etl_task_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_etl_task(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(task.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(task.id)


def test_get_etl_task_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    task = _make_etl_task(workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(task.id))

    assert response.status_code == 404


def test_get_etl_task_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    task = _make_etl_task(workspace)

    response = client.get(_detail_url(task.id))

    assert response.status_code == 401


def test_get_etl_task_returns_404_for_nonexistent_task(client):
    owner = UserFactory()
    client.force_login(owner)

    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- update_etl_task ----------------------------------------------------------------------


def test_update_etl_task_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_etl_task(workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(task.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(task.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_etl_task_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task = _make_etl_task(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(task.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_etl_task ----------------------------------------------------------------------


def test_delete_etl_task_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_etl_task(workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(task.id))

    assert response.status_code == 204
    assert client.get(_detail_url(task.id)).status_code == 404


def test_delete_etl_task_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task = _make_etl_task(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(task.id))

    assert response.status_code == 403


# --- trigger_etl_task (basic verification, no real pipeline execution) --------------------


def test_trigger_etl_task_creates_pending_run_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_etl_task(workspace)
    client.force_login(owner)

    with patch("processing.etl.tasks.run_etl_task.apply_async") as mock_apply_async:
        response = client.post(f"{_detail_url(task.id)}/trigger")

    assert response.status_code == 202
    assert response.json()["status"] == "PENDING"
    mock_apply_async.assert_called_once()
    assert TaskRun.objects.filter(task=task, status="PENDING").exists()


def test_trigger_etl_task_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task = _make_etl_task(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    with patch("processing.etl.tasks.run_etl_task.apply_async") as mock_apply_async:
        response = client.post(f"{_detail_url(task.id)}/trigger")

    assert response.status_code == 403
    mock_apply_async.assert_not_called()


# --- get_etl_task_runs / get_etl_task_run (basic verification only) -----------------------


def test_get_etl_task_runs_returns_runs_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_etl_task(workspace)
    run = TaskRun.objects.create(task=task, status="SUCCESS")
    client.force_login(owner)

    response = client.get(f"{_detail_url(task.id)}/runs")

    assert response.status_code == 200
    assert str(run.id) in [r["id"] for r in response.json()["data"]]


def test_get_etl_task_run_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_etl_task(workspace)
    run = TaskRun.objects.create(task=task, status="SUCCESS")
    client.force_login(owner)

    response = client.get(f"{_detail_url(task.id)}/runs/{run.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(run.id)


def test_get_etl_task_runs_sortby_started_at_ascending(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_etl_task(workspace)
    now = timezone.now()
    older = TaskRun.objects.create(task=task, status="SUCCESS", started_at=now - timedelta(hours=1))
    newer = TaskRun.objects.create(task=task, status="SUCCESS", started_at=now)
    client.force_login(owner)

    response = client.get(f"{_detail_url(task.id)}/runs", {"sortby": "startedAt"})

    assert response.status_code == 200
    ids = [r["id"] for r in response.json()["data"]]
    assert ids == [str(older.id), str(newer.id)]


def test_get_etl_task_runs_sortby_rejects_unknown_field(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_etl_task(workspace)
    client.force_login(owner)

    response = client.get(f"{_detail_url(task.id)}/runs", {"sortby": "bogus"})

    assert response.status_code == 400
