from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlencode

import pytest

from core.sta.models import Observation
from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory

pytestmark = pytest.mark.django_db

OBSERVATIONS_URL = "/api/ogc/collections/observations/items"
BULK_CREATE_URL = "/api/ogc/collections/observations/bulk-create"
BULK_DELETE_URL = "/api/ogc/collections/observations/bulk-delete"
DATASTREAMS_URL = "/api/ogc/collections/datastreams/items"

T0 = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)
T1 = T0 + timedelta(hours=1)


def _owner_and_datastream(client, **kwargs):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)
    return DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=workspace), **kwargs)


def _post(client, url, body, **params):
    if params:
        url = f"{url}?{urlencode(params)}"
    return client.post(url, data=body, content_type="application/json")


def _create(client, datastream, phenomenon_time=T0, **fields):
    body = {"datastreamId": str(datastream.id), "phenomenonTime": phenomenon_time.isoformat(), "result": 1.0, **fields}
    return _post(client, OBSERVATIONS_URL, body)


def _bulk_rows(client, datastream, rows, mode="insert", **params):
    body = {"datastreamId": str(datastream.id), "fields": ["phenomenonTime", "z", "result"], "data": rows}
    return _post(client, BULK_CREATE_URL, body, mode=mode, **params)


def _cast(phenomenon_time, *depths):
    return [[phenomenon_time.isoformat(), z, 1.0] for z in depths]


def _stored_z(datastream):
    return sorted(Observation.objects.filter(datastream=datastream).values_list("phenomenon_time", "z"))


# --- writes -------------------------------------------------------------------------


def test_columnar_bulk_create_stores_z(client):
    datastream = _owner_and_datastream(client, profile=True)
    body = {
        "datastreamId": str(datastream.id),
        "phenomenonTime": [T0.isoformat(), T0.isoformat()],
        "z": [1.0, 2.0],
        "result": [1.0, 2.0],
    }

    response = _post(client, BULK_CREATE_URL, body, mode="insert")

    assert response.status_code == 201
    assert _stored_z(datastream) == [(T0, Decimal("1")), (T0, Decimal("2"))]


def test_create_observation_returns_400_for_z_on_time_series(client):
    datastream = _owner_and_datastream(client)

    response = _create(client, datastream, z=1.0)

    assert response.status_code == 400
    assert not Observation.objects.exists()


@pytest.mark.parametrize("z", [None, float("nan")], ids=["missing", "nan"])
def test_bulk_create_returns_400_for_profile_row_without_numeric_z(client, z):
    datastream = _owner_and_datastream(client, profile=True)

    response = _bulk_rows(client, datastream, [[T0.isoformat(), 1.0, 1.0], [T0.isoformat(), z, 1.0]])

    assert response.status_code == 400
    assert not Observation.objects.exists()


def test_bulk_create_returns_409_for_duplicate_time_and_z(client):
    datastream = _owner_and_datastream(client, profile=True)
    _create(client, datastream, z=1.5)

    response = _bulk_rows(client, datastream, _cast(T0, 1.5))

    assert response.status_code == 409
    assert response.json()["message"] == "Duplicate observation found on this datastream."


@pytest.mark.parametrize(
    "z, stored",
    [(12345678.123456, "12345678.123456"), (0.0000015, "0.000002"), (0.0000025, "0.000002")],
)
def test_single_and_bulk_create_store_z_the_same_way(client, z, stored):
    datastream = _owner_and_datastream(client, profile=True)

    _create(client, datastream, z=z)
    _bulk_rows(client, datastream, _cast(T1, z))

    assert _stored_z(datastream) == [(T0, Decimal(stored)), (T1, Decimal(stored))]


# --- bulk modes ---------------------------------------------------------------------


def test_append_accepts_profile_cast_at_end_time(client):
    datastream = _owner_and_datastream(client, profile=True)
    _bulk_rows(client, datastream, _cast(T0, 1.0))

    response = _bulk_rows(client, datastream, _cast(T0, 2.0) + _cast(T1, 1.0), mode="append")

    assert response.status_code == 201
    assert len(_stored_z(datastream)) == 3


def test_datastream_z_statistics_follow_creates_and_deletes(client):
    datastream = _owner_and_datastream(client, profile=True)
    _bulk_rows(client, datastream, _cast(T0, 0.5, 4.0) + _cast(T1, 9.25))

    created = client.get(f"{DATASTREAMS_URL}/{datastream.id}").json()["data"]
    _post(client, BULK_DELETE_URL, {"datastreamId": str(datastream.id), "phenomenonTimeStart": T1.isoformat()})
    deleted = client.get(f"{DATASTREAMS_URL}/{datastream.id}").json()["data"]

    assert (created["zMin"], created["zMax"], created["valueCount"]) == (0.5, 9.25, 3)
    assert (deleted["zMin"], deleted["zMax"], deleted["valueCount"]) == (0.5, 4.0, 2)


# --- reads --------------------------------------------------------------------------


def test_get_observations_returns_z_as_a_number_in_each_format(client):
    datastream = _owner_and_datastream(client, profile=True)
    _bulk_rows(client, datastream, _cast(T0, 0.5))

    def get(profile=None):
        params = {"datastreamId": str(datastream.id)}
        if profile:
            params["profile"] = f"https://hydroserver.org/profiles/observations/{profile}"
        return client.get(OBSERVATIONS_URL, params).json()["data"]

    rows = get("row")[0]

    assert get()[0]["z"] == 0.5
    assert rows["rows"][0][rows["fields"].index("z")] == 0.5
    assert get("column")[0]["columns"]["z"] == [0.5]


def test_get_observations_filters_by_z_range(client):
    datastream = _owner_and_datastream(client, profile=True)
    _bulk_rows(client, datastream, _cast(T0, 1.0, 2.0, 3.0) + _cast(T1, 2.5))

    response = client.get(OBSERVATIONS_URL, {"datastreamId": str(datastream.id), "minZ": 2.0, "maxZ": 2.5})

    body = response.json()
    assert [record["z"] for record in body["data"]] == [2.0, 2.5]
    assert body["meta"]["numberMatched"] == 2


def test_get_datastream_csv_has_z_column_for_profiles(client):
    datastream = _owner_and_datastream(client, profile=True)
    _bulk_rows(client, datastream, _cast(T0, 2.0, 0.5))

    response = client.get(f"{DATASTREAMS_URL}/{datastream.id}/csv")

    body = b"".join(response.streaming_content).decode()
    assert f"# ZReference: {datastream.z_reference}\n" in body
    assert f"# ZUnit: {datastream.z_unit.name} ({datastream.z_unit.symbol})\n" in body
    assert body.endswith(
        "ResultTime,Z,Result,ResultQualifiers\n"
        f"{T0.isoformat()},0.5,1.0,\n"
        f"{T0.isoformat()},2.0,1.0,\n"
    )
