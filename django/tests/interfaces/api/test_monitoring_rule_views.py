import pytest

from django.test.utils import CaptureQueriesContext
from django.db import connection

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

RULES_URL = "/api/data/monitoring-rules"

MONITORING_RULE_FIELDS = {
    "id",
    "taskId",
    "datastreamId",
    "ruleType",
    "lastCheckedAt",
    "minValue",
    "maxValue",
    "windowInterval",
    "windowIntervalUnits",
}


def _detail_url(rule_id):
    return f"{RULES_URL}/{rule_id}"


def _collaborator_with_permission(workspace, resource_type="MonitoringTask", **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type=resource_type, **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _collaborator_who_can_create_rules(workspace):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="MonitoringTask", can_view=True)
    PermissionFactory(role=role, resource_type="MonitoringRule", can_create=True)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_task_with_datastream(workspace):
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    task = MonitoringTaskFactory(monitoring_site=monitoring_site)
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    return task, datastream


def _rule_body(task_id, datastream_id, **overrides):
    body = {
        "taskId": str(task_id),
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

    response = client.get(RULES_URL, {"task_id": str(task.id)})

    assert response.status_code == 200
    assert str(rule.id) in [r["id"] for r in response.json()["data"]]


def test_get_monitoring_rules_filters_by_workspace_id(client):
    owner = UserFactory()
    workspace_a = WorkspaceFactory(owner=owner)
    workspace_b = WorkspaceFactory(owner=owner)
    task_a, datastream_a = _make_task_with_datastream(workspace_a)
    task_b, datastream_b = _make_task_with_datastream(workspace_b)
    rule_a = MonitoringRuleFactory(task=task_a, datastream=datastream_a)
    MonitoringRuleFactory(task=task_b, datastream=datastream_b)
    client.force_login(owner)

    response = client.get(RULES_URL, {"workspace_id": str(workspace_a.id)})

    assert response.status_code == 200
    assert [r["id"] for r in response.json()["data"]] == [str(rule_a.id)]


def test_get_monitoring_rules_excludes_rules_outside_outsiders_workspaces(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)
    MonitoringRuleFactory(task=task, datastream=datastream)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(RULES_URL, {"workspace_id": str(workspace.id)})

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_get_monitoring_rules_returns_401_when_unauthenticated(client):
    response = client.get(RULES_URL)

    assert response.status_code == 401


def test_get_monitoring_rules_properties_filters_every_item_in_the_list(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    MonitoringRuleFactory(task=task, datastream=datastream, rule_type="missing_data")
    client.force_login(owner)

    response = client.get(RULES_URL, {"task_id": str(task.id), "properties": "id,ruleType"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    for item in items:
        assert set(item.keys()) == {"id", "ruleType"}


def test_get_monitoring_rules_properties_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.get(
        RULES_URL, {"task_id": str(task.id), "properties": ["id", "ruleType"]}
    )

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "ruleType"}


def test_get_monitoring_rules_properties_rejects_unknown_property(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, _ = _make_task_with_datastream(workspace)
    client.force_login(owner)

    response = client.get(RULES_URL, {"task_id": str(task.id), "properties": "id,bogus"})

    assert response.status_code == 400


def test_get_monitoring_rules_without_properties_returns_every_field(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.get(RULES_URL, {"task_id": str(task.id)})

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == MONITORING_RULE_FIELDS


def test_get_monitoring_rules_has_no_included_key_without_include_param(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.get(RULES_URL, {"task_id": str(task.id)})

    assert response.status_code == 200
    assert "included" not in response.json()


def test_get_monitoring_rules_include_datastream_deduplicates_across_items(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    MonitoringRuleFactory(task=task, datastream=datastream, rule_type="missing_data")
    MonitoringRuleFactory(task=task, datastream=datastream, rule_type="persistence")
    client.force_login(owner)

    response = client.get(RULES_URL, {"task_id": str(task.id), "include": "datastream"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert [d["id"] for d in body["included"]["datastreams"]] == [str(datastream.id)]


def test_get_monitoring_rules_include_rejects_unknown_relation(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, _ = _make_task_with_datastream(workspace)
    client.force_login(owner)

    response = client.get(RULES_URL, {"task_id": str(task.id), "include": "bogus"})

    assert response.status_code == 400


def test_get_monitoring_rules_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.get(RULES_URL, {"task_id": str(task.id), "include": ["datastream"]})

    assert response.status_code == 200
    body = response.json()
    assert [d["id"] for d in body["included"]["datastreams"]] == [str(datastream.id)]


def test_get_monitoring_rules_properties_and_include_together(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.get(
        RULES_URL,
        {"task_id": str(task.id), "properties": "id,ruleType", "include": "datastream"},
    )

    assert response.status_code == 200
    body = response.json()
    for item in body["data"]:
        assert set(item.keys()) == {"id", "ruleType"}
    assert body["included"]["datastreams"][0]["id"] == str(datastream.id)


def test_get_monitoring_rules_properties_does_not_filter_included_resources(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    MonitoringRuleFactory(task=task, datastream=datastream, rule_type="missing_data")
    client.force_login(owner)

    response = client.get(
        RULES_URL, {"task_id": str(task.id), "properties": "ruleType", "include": "datastream"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0] == {"ruleType": "missing_data"}
    included_datastream = body["included"]["datastreams"][0]
    assert included_datastream["id"] == str(datastream.id)
    assert included_datastream["name"] == datastream.name


def test_get_monitoring_rules_include_datastream_does_not_scale_queries_with_rule_count(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    for rule_type in ["missing_data", "persistence"]:
        MonitoringRuleFactory(task=task, datastream=datastream, rule_type=rule_type)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(RULES_URL, {"task_id": str(task.id), "include": "datastream"})

    datastream_b = DatastreamFactory(monitoring_site=datastream.monitoring_site)
    for rule_type in ["missing_data", "persistence"]:
        MonitoringRuleFactory(task=task, datastream=datastream_b, rule_type=rule_type)

    with CaptureQueriesContext(connection) as large:
        client.get(RULES_URL, {"task_id": str(task.id), "include": "datastream"})

    assert len(large.captured_queries) == len(small.captured_queries)


def test_get_monitoring_rules_filters_by_datastream_id(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream_a = _make_task_with_datastream(workspace)
    datastream_b = DatastreamFactory(monitoring_site=datastream_a.monitoring_site)
    rule_a = MonitoringRuleFactory(task=task, datastream=datastream_a)
    MonitoringRuleFactory(task=task, datastream=datastream_b)
    client.force_login(owner)

    response = client.get(
        RULES_URL, {"task_id": str(task.id), "datastream_id": str(datastream_a.id)}
    )

    assert response.status_code == 200
    assert [r["id"] for r in response.json()["data"]] == [str(rule_a.id)]


def test_get_monitoring_rules_filters_by_rule_type(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    rule_a = MonitoringRuleFactory(task=task, datastream=datastream, rule_type="missing_data")
    MonitoringRuleFactory(task=task, datastream=datastream, rule_type="persistence")
    client.force_login(owner)

    response = client.get(RULES_URL, {"task_id": str(task.id), "rule_type": "missing_data"})

    assert response.status_code == 200
    assert [r["id"] for r in response.json()["data"]] == [str(rule_a.id)]


def test_get_monitoring_rules_sorts_by_rule_type(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    MonitoringRuleFactory(task=task, datastream=datastream, rule_type="persistence")
    MonitoringRuleFactory(task=task, datastream=datastream, rule_type="missing_data")
    client.force_login(owner)

    response = client.get(RULES_URL, {"task_id": str(task.id), "sortby": "ruleType"})

    assert response.status_code == 200
    assert [r["ruleType"] for r in response.json()["data"]] == [
        "missing_data",
        "persistence",
    ]


def test_get_monitoring_rules_sorts_by_datastream_id(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream_a = _make_task_with_datastream(workspace)
    datastream_b = DatastreamFactory(monitoring_site=datastream_a.monitoring_site)
    MonitoringRuleFactory(task=task, datastream=datastream_a)
    MonitoringRuleFactory(task=task, datastream=datastream_b)
    client.force_login(owner)

    response = client.get(RULES_URL, {"task_id": str(task.id), "sortby": "-datastreamId"})

    datastream_ids_desc = sorted(
        [str(datastream_a.id), str(datastream_b.id)], reverse=True
    )

    assert response.status_code == 200
    assert [r["datastreamId"] for r in response.json()["data"]] == datastream_ids_desc


def test_get_monitoring_rules_sortby_rejects_unknown_field(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, _ = _make_task_with_datastream(workspace)
    client.force_login(owner)

    response = client.get(RULES_URL, {"task_id": str(task.id), "sortby": "bogus"})

    assert response.status_code == 400


# --- create_monitoring_rule -----------------------------------------------------------


def test_create_monitoring_rule_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    client.force_login(owner)

    response = client.post(
        RULES_URL,
        data=_rule_body(task.id, datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}

    detail = client.get(_detail_url(response.json()["id"]))
    body = detail.json()["data"]
    assert body["taskId"] == str(task.id)
    assert body["ruleType"] == "missing_data"
    assert body["datastreamId"] == str(datastream.id)


def test_create_monitoring_rule_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)

    response = client.post(
        RULES_URL,
        data=_rule_body(task.id, datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_monitoring_rule_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        RULES_URL,
        data=_rule_body(task.id, datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_monitoring_rule_succeeds_for_collaborator_with_create_permission(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)
    collaborator = _collaborator_who_can_create_rules(workspace)
    client.force_login(collaborator.user)

    response = client.post(
        RULES_URL,
        data=_rule_body(task.id, datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 201


def test_create_monitoring_rule_returns_404_for_nonexistent_task(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    _, datastream = _make_task_with_datastream(workspace)
    client.force_login(owner)

    response = client.post(
        RULES_URL,
        data=_rule_body("00000000-0000-0000-0000-000000000000", datastream.id),
        content_type="application/json",
    )

    assert response.status_code == 404


def test_create_monitoring_rule_returns_400_when_range_rule_missing_bounds(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    client.force_login(owner)

    response = client.post(
        RULES_URL,
        data=_rule_body(
            task.id,
            datastream.id,
            ruleType="range",
            windowInterval=None,
            windowIntervalUnits=None,
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
        RULES_URL,
        data=_rule_body(task.id, datastream.id),
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

    response = client.get(_detail_url(rule.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(rule.id)


def test_get_monitoring_rule_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(rule.id))

    assert response.status_code == 404


def test_get_monitoring_rule_returns_404_for_nonexistent_rule(client):
    owner = UserFactory()
    WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_monitoring_rule_properties_rejects_unknown_property(client):
    """Single-item GET must validate `properties` the same way the list endpoint
    does -- regression test for a gap where `get_monitoring_rule` had no
    resource-specific query parameter schema at all before this chunk."""
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.get(_detail_url(rule.id), {"properties": "bogus"})

    assert response.status_code == 400


def test_get_monitoring_rule_included_is_present_but_empty_without_include_param(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.get(_detail_url(rule.id))

    assert response.status_code == 200
    body = response.json()
    assert "included" in body
    assert body["included"] == {}


def test_get_monitoring_rule_include_datastream_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.get(_detail_url(rule.id), {"include": "datastream"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(rule.id)
    assert [d["id"] for d in body["included"]["datastreams"]] == [str(datastream.id)]


def test_get_monitoring_rule_include_rejects_unknown_relation(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.get(_detail_url(rule.id), {"include": "bogus"})

    assert response.status_code == 400


def test_get_monitoring_rule_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    client.force_login(owner)

    response = client.get(_detail_url(rule.id), {"include": ["datastream"]})

    assert response.status_code == 200
    body = response.json()
    assert [d["id"] for d in body["included"]["datastreams"]] == [str(datastream.id)]


# --- update_monitoring_rule -----------------------------------------------------------------


def test_update_monitoring_rule_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream, window_interval=1)
    client.force_login(owner)

    response = client.patch(
        _detail_url(rule.id),
        data={"windowInterval": 2},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(rule.id))
    assert detail.json()["data"]["windowInterval"] == 2


def test_update_monitoring_rule_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    collaborator = _collaborator_with_permission(
        workspace, resource_type="MonitoringRule", can_view=True
    )
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(rule.id),
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

    response = client.delete(_detail_url(rule.id))

    assert response.status_code == 204
    assert client.get(_detail_url(rule.id)).status_code == 404


def test_delete_monitoring_rule_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task, datastream = _make_task_with_datastream(workspace)
    rule = MonitoringRuleFactory(task=task, datastream=datastream)
    collaborator = _collaborator_with_permission(
        workspace, resource_type="MonitoringRule", can_view=True
    )
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(rule.id))

    assert response.status_code == 403
