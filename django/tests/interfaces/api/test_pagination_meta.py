from datetime import timedelta

import pytest

from django.utils import timezone

from interfaces.api.formats.profiles import PROFILE_URI_BASE
from tests.core.iam.factories import WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory, ObservationFactory, UnitFactory

pytestmark = pytest.mark.django_db

# A page's meta reports how many items match the request (numberMatched) and how many the page holds
# (numberReturned), along with the page's limit and offset.

UNITS_PATH = "/api/ogc/collections/units/items"
OBSERVATIONS_PATH = "/api/ogc/collections/observations/items"
ROW = f"{PROFILE_URI_BASE}/observations/row"
COLUMN = f"{PROFILE_URI_BASE}/observations/column"


@pytest.fixture
def units():
    return UnitFactory.create_batch(3, global_=True)


@pytest.mark.parametrize("offset", [0, 1, 2, 50], ids=["first page", "middle page", "last page", "past the end"])
@pytest.mark.usefixtures("units")
def test_number_returned_counts_the_items_on_the_page(client, offset):
    body = client.get(UNITS_PATH, {"limit": 2, "offset": offset}).json()
    meta, data = body["meta"], body["data"]

    assert meta["numberReturned"] == len(data) == max(0, min(2, meta["numberMatched"] - offset))
    assert (meta["limit"], meta["offset"]) == (2, offset)


def _observations(datastream, count):
    start = timezone.now() - timedelta(days=1)
    return [
        ObservationFactory(datastream=datastream, phenomenon_time=start + timedelta(minutes=i)) for i in range(count)
    ]


@pytest.fixture
def datastreams():
    workspace = WorkspaceFactory()
    first, second = sorted(
        (DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=workspace)) for _ in range(2)),
        key=lambda datastream: str(datastream.id),
    )
    _observations(first, 2)
    _observations(second, 2)
    return first, second


@pytest.mark.parametrize("profile", [ROW, COLUMN])
def test_number_returned_counts_observations_not_datastream_groups(client, datastreams, profile):
    params = {"datastream_id": [str(datastream.id) for datastream in datastreams], "profile": profile, "limit": 3}

    body = client.get(OBSERVATIONS_PATH, params).json()

    assert len(body["data"]) == 2
    assert body["meta"]["numberReturned"] == 3


def test_number_returned_counts_observations_when_no_column_is_selected(client, datastreams):
    params = {
        "datastream_id": [str(datastream.id) for datastream in datastreams],
        "profile": COLUMN,
        "properties": "datastreamId",
        "limit": 3,
    }

    body = client.get(OBSERVATIONS_PATH, params).json()

    assert all(group["columns"] == {} for group in body["data"])
    assert body["meta"]["numberReturned"] == 3


def test_meta_is_documented_with_both_counts_required(client):
    meta = client.get("/api/ogc/openapi.json").json()["components"]["schemas"]["PaginationMeta"]

    assert {"numberMatched", "numberReturned"} <= set(meta["required"])
    assert "totalCount" not in meta["properties"]
