from datetime import timedelta

import pytest
from django.utils import timezone

from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import (
    DatastreamFactory,
    MonitoringSiteFactory,
    ObservationFactory,
)

pytestmark = pytest.mark.django_db

BASE_URL = "/api/sensorthings/v1.1"


def _names(response):
    assert response.status_code == 200
    return [entity["name"] for entity in response.json()["value"]]


@pytest.mark.parametrize(
    "path, params, expected",
    [
        ("Things", {"$filter": "name ne 'zzz'"}, 200),
        ("Things", {"$filter": "properties/code ne 'x'"}, 200),
        ("Datastreams", {"$filter": "properties/intendedTimeSpacing ne 1"}, 200),
        ("Observations", {"$filter": "result ne 1"}, 200),
        ("Things", {"$expand": "Datastreams($filter=name ne 'q')"}, 200),
        ("Things", {"$filter": "year(name) eq 2020"}, 400),
        ("Observations", {"$filter": "year(result) eq 2020"}, 400),
        ("Things", {"$filter": "name"}, 400),
        ("Things", {"$filter": "name add 1 gt 2"}, 422),
        ("Datastreams", {"$filter": "phenomenonTime gt 2020-01-01T00:00:00Z"}, 200),
        ("Datastreams", {"$filter": "resultTime gt 2020-01-01T00:00:00Z"}, 200),
        ("Datastreams", {"$orderby": "resultTime"}, 200),
        ("Things", {"$orderby": "Datastreams/name"}, 400),
        ("Observations", {"$orderby": "validTime"}, 400),
    ],
)
def test_query_returns_expected_status(client, path, params, expected):
    ObservationFactory()

    assert client.get(f"{BASE_URL}/{path}", params).status_code == expected


def test_ne_filter_excludes_matching_rows(client):
    DatastreamFactory(name="Keep")
    DatastreamFactory(name="Drop")

    response = client.get(f"{BASE_URL}/Datastreams", {"$filter": "name ne 'Drop'"})

    assert _names(response) == ["Keep"]


def test_datastreams_order_by_phenomenon_time(client):
    now = timezone.now()
    DatastreamFactory(name="Later", phenomenon_begin_time=now)
    DatastreamFactory(name="Earlier", phenomenon_begin_time=now - timedelta(days=1))

    response = client.get(f"{BASE_URL}/Datastreams", {"$orderby": "phenomenonTime"})

    assert _names(response) == ["Earlier", "Later"]


def test_post_observation_with_interval_returns_400(client):
    owner = UserFactory()
    site = MonitoringSiteFactory(workspace=WorkspaceFactory(owner=owner))
    datastream = DatastreamFactory(monitoring_site=site)
    client.force_login(owner)

    response = client.post(
        f"{BASE_URL}/Observations",
        data={
            "phenomenonTime": "2020-01-01T00:00:00Z/2020-01-02T00:00:00Z",
            "result": 1.23,
            "Datastream": {"@iot.id": str(datastream.id)},
        },
        content_type="application/json",
    )

    assert response.status_code == 400
