from datetime import timedelta

import pytest
from django.utils import timezone

from interfaces.api.urls import api
from processing.orchestration.models import TaskRun
from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import MonitoringSiteFactory
from tests.processing.etl.factories import DataConnectionFactory, EtlTaskFactory, PayloadFactory

pytestmark = pytest.mark.django_db

# sortby takes comma-separated fields, each with an optional '+' (ascending) or '-' (descending)
# prefix (OGC API - Features Part 8 Req 5). The repeated form (sortby=a&sortby=b) still works.

MONITORING_SITES_URL = "/api/ogc/collections/monitoring-sites/items"


def _names(response):
    return [site["name"] for site in response.json()["data"]]


@pytest.fixture
def sites():
    MonitoringSiteFactory(name="b", code="1")
    MonitoringSiteFactory(name="a", code="1")
    MonitoringSiteFactory(name="a", code="2")


@pytest.mark.parametrize(
    "query",
    [
        "sortby=name,-code",
        "sortby=name&sortby=-code",
        "sortby=%2Bname,-code",
        "sortby=%2Bname&sortby=-code",
    ],
)
def test_get_items_sorts_by_comma_separated_or_repeated_fields(client, sites, query):
    response = client.get(f"{MONITORING_SITES_URL}?{query}")

    assert response.status_code == 200
    assert [(s["name"], s["code"]) for s in response.json()["data"]] == [("a", "2"), ("a", "1"), ("b", "1")]


def test_get_items_treats_an_unencoded_plus_as_ascending(client, sites):
    # An unencoded '+' in a query string decodes to a space.
    response = client.get(f"{MONITORING_SITES_URL}?sortby=+name")

    assert response.status_code == 200
    assert _names(response) == ["a", "a", "b"]


@pytest.mark.parametrize(
    "sortby", ["name,%2Bname", "name,-name", "bogus", "%2B-name", "%2B%2Bname", "%2B"]
)
def test_get_items_returns_400_for_invalid_sortby(client, sortby):
    response = client.get(f"{MONITORING_SITES_URL}?sortby={sortby}")

    assert response.status_code == 400


def _etl_task(owner):
    data_connection = DataConnectionFactory(workspace=WorkspaceFactory(owner=owner))
    PayloadFactory(data_connection=data_connection)
    return EtlTaskFactory(data_connection=data_connection)


def test_get_task_runs_accepts_a_plus_prefix(client):
    owner = UserFactory()
    task = _etl_task(owner)
    now = timezone.now()
    older = TaskRun.objects.create(task=task, status="SUCCESS", started_at=now - timedelta(hours=1))
    newer = TaskRun.objects.create(task=task, status="SUCCESS", started_at=now)
    client.force_login(owner)

    response = client.get(f"/api/ogc/collections/etl-tasks/items/{task.id}/runs?sortby=%2BstartedAt")

    assert response.status_code == 200
    assert [run["id"] for run in response.json()["data"]] == [str(older.id), str(newer.id)]


def test_get_etl_tasks_accepts_a_plus_prefix_on_latest_run_fields(client):
    owner = UserFactory()
    now = timezone.now()
    older = _etl_task(owner)
    TaskRun.objects.create(task=older, status="SUCCESS", started_at=now - timedelta(hours=1))
    newer = _etl_task(owner)
    TaskRun.objects.create(task=newer, status="SUCCESS", started_at=now)
    client.force_login(owner)

    response = client.get("/api/ogc/collections/etl-tasks/items?sortby=%2BlatestRunStartedAt")

    assert response.status_code == 200
    ids = [task["id"] for task in response.json()["data"]]
    assert ids.index(str(older.id)) < ids.index(str(newer.id))


def test_every_sortby_parameter_is_comma_separated_with_plus_and_minus_prefixes():
    paths = api.get_openapi_schema(path_prefix="/api/ogc/")["paths"]
    sortby_parameters = [
        parameter
        for path_item in paths.values()
        for operation in path_item.values()
        for parameter in operation.get("parameters", [])
        if parameter["name"] == "sortby"
    ]

    assert sortby_parameters
    for parameter in sortby_parameters:
        assert parameter["style"] == "form"
        assert parameter["explode"] is False
        assert parameter["schema"]["type"] == "array"
        values = set(parameter["schema"]["items"]["enum"])
        ascending = {value for value in values if value[0] not in "+-"}
        assert values == ascending | {f"+{f}" for f in ascending} | {f"-{f}" for f in ascending}
