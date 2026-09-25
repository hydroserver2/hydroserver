import pytest

from interfaces.api.http.errors import BadRequestError
from interfaces.api.schemas import base
from interfaces.api.service import APIService
from interfaces.api.urls import api
from processing.orchestration.models import TaskRun
from core.iam.models import Workspace
from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory, ObservationFactory
from tests.processing.etl.factories import DataConnectionFactory, EtlTaskFactory, PayloadFactory

pytestmark = pytest.mark.django_db

# A limit above the maximum isn't an error; the maximum is used instead (OGC API - Features
# Core Req 22C). Tests that count returned items lower the maximum so they don't need 100k rows.

MONITORING_SITES_URL = "/api/ogc/collections/monitoring-sites/items"


@pytest.fixture
def max_limit_of_two(monkeypatch):
    monkeypatch.setattr(base, "MAX_LIMIT", 2)


def test_get_items_uses_the_maximum_when_limit_is_larger(client):
    response = client.get(MONITORING_SITES_URL, {"limit": 200000})

    assert response.status_code == 200
    assert response.json()["meta"]["limit"] == 100000


def test_get_items_returns_at_most_the_maximum_number_of_items(client, max_limit_of_two):
    MonitoringSiteFactory.create_batch(3)

    response = client.get(MONITORING_SITES_URL, {"limit": 5})

    assert response.status_code == 200
    assert len(response.json()["data"]) == 2
    assert response.json()["meta"]["limit"] == 2


def test_get_observations_row_format_uses_the_maximum(client, max_limit_of_two):
    datastream = DatastreamFactory()
    ObservationFactory.create_batch(3, datastream=datastream)

    response = client.get(
        "/api/ogc/collections/observations/items",
        {"datastream_id": str(datastream.id), "format": "row", "limit": 5},
    )

    assert response.status_code == 200
    assert len(response.json()["data"]["rows"]) == 2


def test_get_task_runs_uses_the_maximum(client, max_limit_of_two):
    owner = UserFactory()
    data_connection = DataConnectionFactory(workspace=WorkspaceFactory(owner=owner))
    PayloadFactory(data_connection=data_connection)
    task = EtlTaskFactory(data_connection=data_connection)
    for _ in range(3):
        TaskRun.objects.create(task=task, status="SUCCESS")
    client.force_login(owner)

    response = client.get(f"/api/ogc/collections/etl-tasks/items/{task.id}/runs", {"limit": 5})

    assert response.status_code == 200
    assert len(response.json()["data"]) == 2
    assert response.json()["meta"]["limit"] == 2


def test_get_items_returns_400_for_a_negative_limit(client):
    response = client.get(MONITORING_SITES_URL, {"limit": -1})

    assert response.status_code == 400


def test_limit_declares_the_maximum_in_the_openapi_document():
    parameters = api.get_openapi_schema(path_prefix="/api/ogc/")["paths"][MONITORING_SITES_URL]["get"][
        "parameters"
    ]
    limit = next(p for p in parameters if p["name"] == "limit")

    assert limit["schema"]["type"] == "integer"
    assert limit["schema"]["minimum"] == 0
    assert limit["schema"]["maximum"] == 100000


def test_apply_pagination_uses_the_maximum_when_limit_is_larger(max_limit_of_two):
    WorkspaceFactory.create_batch(3)

    page, meta = APIService.apply_pagination(Workspace.objects.order_by("pk"), limit=5)

    assert len(page) == 2
    assert meta.limit == 2


def test_apply_pagination_rejects_a_negative_limit():
    with pytest.raises(BadRequestError):
        APIService.apply_pagination(Workspace.objects.all(), limit=-1)
