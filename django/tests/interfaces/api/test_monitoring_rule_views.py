import pytest

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory
from tests.processing.monitoring.factories import MonitoringRuleFactory, MonitoringTaskFactory

pytestmark = pytest.mark.django_db

MONITORING_TASKS_URL = "/api/data/monitoring/tasks"


def _rules_url(task_id):
    return f"{MONITORING_TASKS_URL}/{task_id}/rules"


def _detail_url(task_id, rule_id):
    return f"{_rules_url(task_id)}/{rule_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="MonitoringTask", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_task_with_datastream(workspace):
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    task = MonitoringTaskFactory(monitoring_site=monitoring_site)
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    return task, datastream


def _rule_body(datastream_id, **overrides):
    body = {
        "datastreamId": str(datastream_id),
        "ruleType": "missing_data",
        "windowInterval": 1,
        "windowIntervalUnits": "days",
    }
    body.update(overrides)
    return body


# --- get_monitoring_rules ------------------------------------------------------------


def test_get_monitoring_rules_includes_rule_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.get(_rules_url(task.id))

    assert response.status_code == 200
    assert str(rule.id) in [r["id"] for r in response.json()]


def test_get_monitoring_rules_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)
    MonitoringRuleFactory(task=task, datastream=datastream)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_rules_url(task.id))

    assert response.status_code == 404


def test_get_monitoring_rules_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)

    response = client.get(_rules_url(task.id))

    assert response.status_code == 401


# --- create_monitoring_rule -----------------------------------------------------------


def test_create_monitoring_rule_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    client.force_login(owner)

    response = client.post(
        _rules_url(task.id),
        data=_rule_body(datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["ruleType"] == "missing_data"


def test_create_monitoring_rule_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)

    response = client.post(
        _rules_url(task.id),
        data=_rule_body(datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_monitoring_rule_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        _rules_url(task.id),
        data=_rule_body(datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_monitoring_rule_returns_400_when_range_rule_missing_bounds(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    client.force_login(owner)

    response = client.post(
        _rules_url(task.id),
        data=_rule_body(
            datastream.id, ruleType="range", windowInterval=None, windowIntervalUnits=None
        ),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_monitoring_rule_returns_400_for_duplicate_rule_type_on_datastream(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.post(
        _rules_url(task.id),
        data=_rule_body(datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_monitoring_rule -----------------------------------------------------------------


def test_get_monitoring_rule_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.get(_detail_url(task.id, rule.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(rule.id)


def test_get_monitoring_rule_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(task.id, rule.id))

    assert response.status_code == 404


def test_get_monitoring_rule_returns_404_for_nonexistent_rule(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, _ = _make_task_with_datastream(workspace)
    client.force_login(owner)

    response = client.get(
        _detail_url(task.id, "00000000-0000-0000-0000-000000000000")
    )

    assert response.status_code == 404


# --- update_monitoring_rule -----------------------------------------------------------------


def test_update_monitoring_rule_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream, window_interval=1)
    client.force_login(owner)

    response = client.patch(
        _detail_url(task.id, rule.id),
        data={"windowInterval": 2},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["windowInterval"] == 2


def test_update_monitoring_rule_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(task.id, rule.id),
        data={"windowInterval": 2},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_monitoring_rule -----------------------------------------------------------------


def test_delete_monitoring_rule_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.delete(_detail_url(task.id, rule.id))

    assert response.status_code == 204
    assert client.get(_detail_url(task.id, rule.id)).status_code == 404


def test_delete_monitoring_rule_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(task.id, rule.id))

    assert response.status_code == 403
