from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import pytest

from interfaces.api.services.sta.datastream import DatastreamAPIService, OBSERVATION_STATISTICS_FIELDS
from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory, ObservationFactory

pytestmark = pytest.mark.django_db

# Filtering, formats, property selection, includes and permissions come from the pipeline the latest observations
# collection shares with the observations collection, so those are tested there. These tests cover what the latest
# observations collection adds: which observations count as latest, its datastream filters, and its item route.

ITEMS_URL = "/api/ogc/collections/latest-observations/items"
BULK_DELETE_URL = "/api/ogc/collections/observations/bulk-delete"

T0 = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)
T1 = T0 + timedelta(hours=1)
T2 = T0 + timedelta(hours=2)


def _url(**params):
    return f"{ITEMS_URL}?{urlencode(params, doseq=True)}" if params else ITEMS_URL


def _make_datastream(workspace=None, site=None, **kwargs):
    site = site or MonitoringSiteFactory(workspace=workspace or WorkspaceFactory())
    return DatastreamFactory(monitoring_site=site, **kwargs)


def _observe(datastream, *rows):
    """
    Stores (phenomenon_time, z, result) rows on a datastream, then refreshes its statistics the way every write
    path does, which sets the phenomenon_end_time the latest observations collection matches on.
    """

    observations = [
        ObservationFactory(datastream=datastream, phenomenon_time=phenomenon_time, z=z, result=result)
        for phenomenon_time, z, result in rows
    ]
    DatastreamAPIService.update_observation_statistics(datastream, OBSERVATION_STATISTICS_FIELDS)
    return observations


def _ids(response):
    return {item["id"] for item in response.json()["data"]}


def test_returns_the_latest_observation_of_each_datastream(client):
    datastream = _make_datastream()
    no_data = _make_datastream(no_data_value=-9999)
    _make_datastream()  # no observations, so no latest observation
    _, latest = _observe(datastream, (T0, None, 1.0), (T1, None, 2.0))
    _, latest_no_data = _observe(no_data, (T0, None, 1.0), (T2, None, -9999.0))

    response = client.get(_url())

    assert response.status_code == 200
    assert _ids(response) == {str(latest.id), str(latest_no_data.id)}
    assert response.json()["meta"]["numberMatched"] == 2


def test_returns_every_z_at_the_latest_time_of_a_profile_datastream(client):
    datastream = _make_datastream(profile=True)
    _, _, deep, shallow = _observe(datastream, (T0, 1, 1.0), (T0, 2, 2.0), (T1, 2, 3.0), (T1, 1, 4.0))

    response = client.get(_url(datastreamId=str(datastream.id)))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(shallow.id), str(deep.id)]


def test_returns_the_previous_time_after_the_latest_is_deleted(client):
    owner = UserFactory()
    datastream = _make_datastream(WorkspaceFactory(owner=owner))
    previous, _ = _observe(datastream, (T0, None, 1.0), (T1, None, 2.0))
    client.force_login(owner)

    client.post(
        BULK_DELETE_URL,
        data={"datastreamId": str(datastream.id), "phenomenonTimeStart": T1.isoformat()},
        content_type="application/json",
    )
    response = client.get(_url(datastreamId=str(datastream.id)))

    assert _ids(response) == {str(previous.id)}


def test_filters_on_datastream_attributes(client):
    workspace = WorkspaceFactory()
    site = MonitoringSiteFactory(workspace=workspace)
    datastream = _make_datastream(site=site)
    elsewhere = _make_datastream(profile=True)
    (latest,) = _observe(datastream, (T0, None, 1.0))
    _observe(elsewhere, (T0, 1, 1.0))

    for params in (
        {"workspaceId": str(workspace.id)},
        {"monitoringSiteId": str(site.id)},
        {"observedPropertyId": str(datastream.observed_property_id)},
        {"processingLevelId": str(datastream.processing_level_id)},
        {"methodId": str(datastream.method_id)},
        {"unitId": str(datastream.unit_id)},
        {"type": "timeSeriesCoverage"},
    ):
        response = client.get(_url(**params))

        assert response.status_code == 200, params
        assert _ids(response) == {str(latest.id)}, params


def test_datetime_matches_datastreams_whose_latest_falls_in_the_interval(client):
    recent = _make_datastream()
    stale = _make_datastream()
    (recent_latest,) = _observe(recent, (T2, None, 1.0))
    _observe(stale, (T0, None, 1.0))

    response = client.get(_url(datetime=f"{T1.isoformat()}/..".replace("+00:00", "Z")))

    assert response.status_code == 200
    assert _ids(response) == {str(recent_latest.id)}


def test_item_is_found_only_while_it_is_the_latest(client):
    datastream = _make_datastream()
    previous, latest = _observe(datastream, (T0, None, 1.0), (T1, None, 2.0))

    assert client.get(f"{ITEMS_URL}/{latest.id}").status_code == 200
    assert client.get(f"{ITEMS_URL}/{previous.id}").status_code == 404


def test_hides_latest_observations_of_private_and_restricted_datastreams_from_anonymous(client):
    _observe(_make_datastream(private=True), (T0, None, 1.0))
    _observe(_make_datastream(restricted=True), (T0, None, 1.0))

    response = client.get(_url())

    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"]["numberMatched"] == 0
