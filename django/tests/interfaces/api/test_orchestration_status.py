from datetime import timedelta

import pytest
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from processing.orchestration.models import TaskRun
from processing.orchestration.status import annotate_task_status
from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import MonitoringSiteFactory
from tests.processing.etl.factories import DataConnectionFactory, EtlTaskFactory
from tests.processing.monitoring.factories import MonitoringTaskFactory
from tests.processing.products.factories import DataProductTaskFactory

pytestmark = pytest.mark.django_db


def schedule(task, enabled=True):
    interval, _ = IntervalSchedule.objects.get_or_create(every=1, period="hours")
    task.periodic_task = PeriodicTask.objects.create(
        name=str(task.pk), task="test", interval=interval, enabled=enabled,
    )
    task.next_run_at = timezone.now() - timedelta(hours=1)
    task.save()


@pytest.mark.parametrize("run_status,result,enabled,next_run,expected", [
    (None, None, None, None, "Pending"),
    ("SUCCESS", None, None, None, "OK"),
    ("SUCCESS", {"rules_violated": 0, "violations": []}, True, 1, "OK"),
    ("SUCCESS", None, True, -1, "Behind schedule"),
    ("SUCCESS", None, True, None, "Unknown"),
    ("STARTED", None, True, -1, "Pending"),
    ("PENDING", None, True, -1, "Pending"),
    (None, None, True, -1, "Pending"),
    (None, None, False, -1, "Loading paused"),
    ("SUCCESS", None, False, -1, "Loading paused"),
    ("STARTED", None, False, -1, "Loading paused"),
    ("FAILURE", {"rules_violated": 2}, False, -1, "Needs attention"),
    ("SUCCESS", {"rules_violated": 2}, True, -1, "Violations found"),
    ("SUCCESS", {"rulesViolated": 2}, None, None, "Violations found"),
    ("SUCCESS", {"violations": [{"rule_id": "rule"}]}, False, -1, "Violations found"),
    ("PENDING", {"rules_violated": 2}, True, -1, "Pending"),
])
def test_task_status_precedence(run_status, result, enabled, next_run, expected):
    task = MonitoringTaskFactory()
    now = timezone.now()
    if enabled is not None:
        schedule(task, enabled)
        task.next_run_at = now + timedelta(hours=next_run) if next_run is not None else None
        task.save()
    if run_status:
        TaskRun.objects.create(task=task, status=run_status, result=result)

    assert annotate_task_status(type(task).objects, now=now).get(pk=task.pk).status == expected


@pytest.mark.parametrize("kind,factory", [
    ("etl", EtlTaskFactory),
    ("data-product", DataProductTaskFactory),
    ("monitoring", MonitoringTaskFactory),
])
def test_api_status_filter_sort_and_pagination_agree_with_detail(client, kind, factory):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    if kind == "etl":
        parent = {"data_connection": DataConnectionFactory(workspace=workspace)}
    else:
        parent = {"monitoring_site": MonitoringSiteFactory(workspace=workspace)}
    tasks = {}
    for execution, display in [("SUCCESS", "OK"), ("FAILURE", "Needs attention"), ("PENDING", "Pending")]:
        task = factory(**parent)
        TaskRun.objects.create(task=task, status=execution)
        tasks[display] = task
    client.force_login(owner)
    url = f"/api/ogc/collections/{kind}-tasks/items"

    response = client.get(url, {"sortby": "status", "limit": 1, "offset": 1})
    assert response.status_code == 200
    assert response.json()["meta"]["numberMatched"] == 3
    assert response.json()["data"][0]["status"] == "OK"

    response = client.get(url, {"status": "Needs attention", "properties": "id,status"})
    assert response.status_code == 200
    assert response.json()["meta"]["numberMatched"] == 1
    assert response.json()["data"] == [{"id": str(tasks["Needs attention"].pk), "status": "Needs attention"}]

    for status, task in tasks.items():
        detail = client.get(f"{url}/{task.pk}").json()["data"]
        assert detail["status"] == status
        assert detail["latestRun"]["displayStatus"] == status
        run = client.get(f"{url}/{task.pk}/runs").json()["data"][0]
        assert run["displayStatus"] == status
        single_run = client.get(f"{url}/{task.pk}/runs/{run['id']}").json()["data"]
        assert single_run["displayStatus"] == status


def test_quality_violations_and_errors_have_distinct_filters_and_share_badge_count(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    site = MonitoringSiteFactory(workspace=workspace)
    task = MonitoringTaskFactory(monitoring_site=site)
    schedule(task, enabled=False)
    TaskRun.objects.create(task=task, status="FAILURE", started_at=timezone.now() - timedelta(days=1))
    run = TaskRun.objects.create(task=task, status="SUCCESS", result={"rules_violated": 2})
    failed_task = MonitoringTaskFactory(monitoring_site=site)
    TaskRun.objects.create(task=failed_task, status="FAILURE")
    MonitoringTaskFactory(monitoring_site=site)
    client.force_login(owner)
    url = "/api/ogc/collections/monitoring-tasks/items"

    for status, expected_task in [("Violations found", task), ("Needs attention", failed_task)]:
        response = client.get(url, {"status": status})
        assert response.status_code == 200
        assert response.json()["meta"]["numberMatched"] == 1
        assert response.json()["data"][0]["id"] == str(expected_task.pk)
        assert response.json()["data"][0]["status"] == status

    history = client.get(f"{url}/{task.pk}/runs/{run.pk}").json()["data"]
    assert history["status"] == "SUCCESS"
    assert history["displayStatus"] == "Violations found"

    summary_url = "/api/ogc/collections/monitoring-sites/task-summaries"
    summary = client.get(summary_url).json()[0]
    assert summary["monitoringTaskCount"] == 3
    assert summary["monitoringTaskAttentionCount"] == 2

    # The same deterministic ID tie-break drives task lists and badges.
    TaskRun.objects.create(task=task, status="SUCCESS", started_at=run.started_at, id="ffffffff-ffff-ffff-ffff-ffffffffffff")
    assert client.get(f"{url}/{task.pk}").json()["data"]["status"] == "Loading paused"
    assert client.get(summary_url).json()[0]["monitoringTaskAttentionCount"] == 1


def test_data_connection_badge_uses_same_statuses_as_tasks():
    from interfaces.api.services.etl.data_connection import DataConnectionAPIService

    connection = DataConnectionFactory()
    for status, enabled in [("FAILURE", False), ("SUCCESS", True), ("SUCCESS", False), ("STARTED", True)]:
        task = EtlTaskFactory(data_connection=connection)
        schedule(task, enabled)
        TaskRun.objects.create(task=task, status=status)

    annotated = DataConnectionAPIService.annotate_task_counts(type(connection).objects).get(pk=connection.pk)
    assert annotated.task_count == 4
    assert annotated.task_attention_count == 2
