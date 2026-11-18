from decimal import Decimal

import pytest

from core.sta.models import Datastream
from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import (
    DatastreamFactory,
    MethodFactory,
    MonitoringSiteFactory,
    ObservedPropertyFactory,
    ProcessingLevelFactory,
    UnitFactory,
    ZReferenceFactory,
)

pytestmark = pytest.mark.django_db

DATASTREAMS_COLLECTION_URL = "/api/ogc/collections/datastreams"
DATASTREAMS_URL = f"{DATASTREAMS_COLLECTION_URL}/items"


def _detail_url(datastream_id):
    return f"{DATASTREAMS_URL}/{datastream_id}"


def _owner_and_workspace(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)
    return owner, workspace


def _make_datastream(workspace, **kwargs):
    return DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=workspace), **kwargs)


def _profile_body(workspace, **overrides):
    body = {
        "name": "Temperature profile",
        "description": "Water temperature profiles at the forebay.",
        "type": "profileCoverage",
        "zReference": "Depth below water surface",
        "zUnitId": str(UnitFactory(workspace=workspace, name="Meter", symbol="m").id),
        "monitoringSiteId": str(MonitoringSiteFactory(workspace=workspace).id),
        "methodId": str(MethodFactory(workspace=workspace).id),
        "observedPropertyId": str(ObservedPropertyFactory(workspace=workspace).id),
        "processingLevelId": str(ProcessingLevelFactory(workspace=workspace).id),
        "unitId": str(UnitFactory(workspace=workspace).id),
        "sampledMedium": "Water",
        "noDataValue": -9999.0,
        "aggregationStatistic": "Continuous",
        "timeAggregationInterval": 0,
        "timeAggregationIntervalUnit": "seconds",
    }
    body.update(overrides)
    return body


# --- create -------------------------------------------------------------------------


def test_create_profile_datastream_returns_z_fields(client):
    _, workspace = _owner_and_workspace(client)
    body = _profile_body(workspace)

    response = client.post(DATASTREAMS_URL, data=body, content_type="application/json")

    assert response.status_code == 201
    data = client.get(_detail_url(response.json()["id"])).json()["data"]
    assert data["type"] == "profileCoverage"
    assert data["zReference"] == "Depth below water surface"
    assert data["zUnitId"] == body["zUnitId"]
    assert data["zMin"] is None
    assert data["zMax"] is None


def test_create_profile_datastream_returns_400_without_z_reference(client):
    _, workspace = _owner_and_workspace(client)
    body = _profile_body(workspace)
    del body["zReference"]

    response = client.post(DATASTREAMS_URL, data=body, content_type="application/json")

    assert response.status_code == 400
    assert not Datastream.objects.exists()


def test_create_time_series_datastream_returns_400_with_z_reference(client):
    _, workspace = _owner_and_workspace(client)
    body = _profile_body(workspace, type="timeSeriesCoverage")
    del body["zUnitId"]

    response = client.post(DATASTREAMS_URL, data=body, content_type="application/json")

    assert response.status_code == 400


def test_get_profile_datastream_returns_z_statistics_as_numbers(client):
    _, workspace = _owner_and_workspace(client)
    datastream = _make_datastream(workspace, profile=True, z_min=Decimal("0.5"), z_max=Decimal("42.125"))

    data = client.get(_detail_url(datastream.id)).json()["data"]

    assert data["zMin"] == 0.5
    assert data["zMax"] == 42.125


# --- update -------------------------------------------------------------------------


def test_update_datastream_accepts_unchanged_type(client):
    _, workspace = _owner_and_workspace(client)
    datastream = _make_datastream(workspace, profile=True)

    response = client.patch(
        _detail_url(datastream.id),
        data={"type": "profileCoverage", "name": "Renamed"},
        content_type="application/json",
    )

    assert response.status_code == 204
    datastream.refresh_from_db()
    assert datastream.name == "Renamed"


def test_update_datastream_returns_400_for_changed_type(client):
    _, workspace = _owner_and_workspace(client)
    datastream = _make_datastream(workspace)

    response = client.patch(
        _detail_url(datastream.id),
        data={
            "type": "profileCoverage",
            "zReference": "Depth below water surface",
            "zUnitId": str(UnitFactory(workspace=workspace).id),
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    datastream.refresh_from_db()
    assert datastream.type == "timeSeriesCoverage"


def test_update_profile_datastream_changes_z_fields(client):
    _, workspace = _owner_and_workspace(client)
    datastream = _make_datastream(workspace, profile=True)
    new_unit = UnitFactory(workspace=workspace)

    response = client.patch(
        _detail_url(datastream.id),
        data={"zReference": "Height above streambed", "zUnitId": str(new_unit.id)},
        content_type="application/json",
    )

    assert response.status_code == 204
    datastream.refresh_from_db()
    assert datastream.z_reference == "Height above streambed"
    assert datastream.z_unit_id == new_unit.id


def test_update_profile_datastream_returns_400_for_cleared_z_unit(client):
    _, workspace = _owner_and_workspace(client)
    datastream = _make_datastream(workspace, profile=True)

    response = client.patch(_detail_url(datastream.id), data={"zUnitId": None}, content_type="application/json")

    assert response.status_code == 400
    datastream.refresh_from_db()
    assert datastream.z_unit_id is not None


# --- list: filters and includes -----------------------------------------------------


def test_get_datastreams_filters_by_type(client):
    _, workspace = _owner_and_workspace(client)
    profile = _make_datastream(workspace, profile=True)
    _make_datastream(workspace)

    response = client.get(DATASTREAMS_URL, {"type": "profileCoverage", "workspaceId": str(workspace.id)})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(profile.id)]


def test_get_datastreams_filters_by_z_reference_and_z_unit(client):
    _, workspace = _owner_and_workspace(client)
    match = _make_datastream(workspace, profile=True, z_reference="Height above streambed")
    _make_datastream(workspace, profile=True)

    by_reference = client.get(DATASTREAMS_URL, {"zReference": "Height above streambed"})
    by_unit = client.get(DATASTREAMS_URL, {"zUnitId": str(match.z_unit_id)})

    assert [item["id"] for item in by_reference.json()["data"]] == [str(match.id)]
    assert [item["id"] for item in by_unit.json()["data"]] == [str(match.id)]


def test_get_datastream_include_unit_and_z_unit_share_units_bucket(client):
    _, workspace = _owner_and_workspace(client)
    datastream = _make_datastream(workspace, profile=True)

    response = client.get(_detail_url(datastream.id), {"include": "unit,zUnit"})

    assert response.status_code == 200
    assert {row["id"] for row in response.json()["included"]["units"]} == {
        str(datastream.unit_id),
        str(datastream.z_unit_id),
    }


def test_get_datastream_include_z_reference_sideloads_vocabulary_term(client):
    _, workspace = _owner_and_workspace(client)
    term = ZReferenceFactory(name="Depth below water surface")
    datastream = _make_datastream(workspace, profile=True, z_reference=term.name)

    response = client.get(_detail_url(datastream.id), {"include": "zReference"})

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["included"]["zReferences"]] == [str(term.id)]


# --- visualization bootstrap --------------------------------------------------------


def test_visualization_bootstrap_returns_profile_fields(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(
        workspace,
        profile=True,
        z_unit=UnitFactory(workspace=workspace, symbol="m"),
    )
    time_series = _make_datastream(workspace)

    response = client.get(f"{DATASTREAMS_COLLECTION_URL}/visualization-bootstrap")

    assert response.status_code == 200
    by_id = {d["id"]: d for d in response.json()["datastreams"]}
    assert by_id[str(datastream.id)]["type"] == "profileCoverage"
    assert by_id[str(datastream.id)]["zReference"] == "Depth below water surface"
    assert by_id[str(datastream.id)]["zUnitId"] == str(datastream.z_unit_id)
    assert by_id[str(datastream.id)]["zUnitSymbol"] == "m"
    assert by_id[str(time_series.id)]["type"] == "timeSeriesCoverage"
    assert by_id[str(time_series.id)]["zUnitId"] is None
