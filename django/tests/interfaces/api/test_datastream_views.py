import pytest

from core.sta.models import (
    DatastreamAggregation,
    DatastreamStatus,
    DatastreamTag,
    FileAttachmentType,
    SampledMedium,
)
from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import (
    DatastreamFactory,
    ObservationFactory,
    ObservedPropertyFactory,
    ProcessingLevelFactory,
    MethodFactory,
    MonitoringSiteFactory,
    UnitFactory,
)

pytestmark = pytest.mark.django_db

DATASTREAMS_URL = "/api/data/datastreams"


def _detail_url(datastream_id):
    return f"{DATASTREAMS_URL}/{datastream_id}"


def _tags_url(datastream_id):
    return f"{_detail_url(datastream_id)}/tags"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Datastream", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_datastream(workspace, **kwargs):
    return DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=workspace), **kwargs)


def _datastream_body(monitoring_site, method, observed_property, processing_level, unit, **overrides):
    body = {
        "name": "New Datastream",
        "description": "A new datastream.",
        "monitoringSiteId": str(monitoring_site.id),
        "methodId": str(method.id),
        "observedPropertyId": str(observed_property.id),
        "processingLevelId": str(processing_level.id),
        "unitId": str(unit.id),
        "observationType": "OM_Measurement",
        "resultType": "Time Series Coverage",
        "sampledMedium": "Water",
        "noDataValue": -9999.0,
        "aggregationStatistic": "Average",
        "timeAggregationInterval": 15,
        "timeAggregationIntervalUnit": "minutes",
        "isPrivate": False,
        "isVisible": True,
    }
    body.update(overrides)
    return body


# --- get_datastreams ---------------------------------------------------------------


def test_get_datastreams_includes_public_datastream_for_anonymous(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)

    response = client.get(DATASTREAMS_URL)

    assert response.status_code == 200
    assert str(datastream.id) in [d["id"] for d in response.json()]


def test_get_datastreams_excludes_private_datastream_for_outsider(client):
    workspace = WorkspaceFactory()
    _make_datastream(workspace, private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(DATASTREAMS_URL)

    assert response.json() == []


def test_get_datastreams_includes_private_datastream_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace, private=True)
    client.force_login(owner)

    response = client.get(DATASTREAMS_URL)

    assert response.status_code == 200
    assert str(datastream.id) in [d["id"] for d in response.json()]


# --- create_datastream ---------------------------------------------------------------


def test_create_datastream_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    method = MethodFactory(workspace=workspace)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    processing_level = ProcessingLevelFactory(workspace=workspace)
    unit = UnitFactory(workspace=workspace)
    client.force_login(owner)

    response = client.post(
        DATASTREAMS_URL,
        data=_datastream_body(monitoring_site, method, observed_property, processing_level, unit),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["name"] == "New Datastream"


def test_create_datastream_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    method = MethodFactory(workspace=workspace)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    processing_level = ProcessingLevelFactory(workspace=workspace)
    unit = UnitFactory(workspace=workspace)

    response = client.post(
        DATASTREAMS_URL,
        data=_datastream_body(monitoring_site, method, observed_property, processing_level, unit),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_datastream_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    method = MethodFactory(workspace=workspace)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    processing_level = ProcessingLevelFactory(workspace=workspace)
    unit = UnitFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        DATASTREAMS_URL,
        data=_datastream_body(monitoring_site, method, observed_property, processing_level, unit),
        content_type="application/json",
    )

    assert response.status_code == 403


# --- vocabulary endpoints ------------------------------------------------------------


def test_get_datastream_aggregation_statistics_returns_registered_type_names(client):
    DatastreamAggregation.objects.create(name="Average")
    DatastreamAggregation.objects.create(name="Maximum")

    response = client.get(f"{DATASTREAMS_URL}/aggregation-statistics")

    assert response.status_code == 200
    assert set(response.json()) == {"Average", "Maximum"}


def test_get_datastream_statuses_returns_registered_type_names(client):
    DatastreamStatus.objects.create(name="Ongoing")
    DatastreamStatus.objects.create(name="Completed")

    response = client.get(f"{DATASTREAMS_URL}/statuses")

    assert response.status_code == 200
    assert set(response.json()) == {"Ongoing", "Completed"}


def test_get_datastream_sampled_mediums_returns_registered_type_names(client):
    SampledMedium.objects.create(name="Water")
    SampledMedium.objects.create(name="Air")

    response = client.get(f"{DATASTREAMS_URL}/sampled-mediums")

    assert response.status_code == 200
    assert set(response.json()) == {"Water", "Air"}


def test_get_datastream_file_attachment_types_returns_registered_type_names(client):
    FileAttachmentType.objects.create(name="Photo")
    FileAttachmentType.objects.create(name="Report")

    response = client.get(f"{DATASTREAMS_URL}/file-attachment-types")

    assert response.status_code == 200
    assert set(response.json()) == {"Photo", "Report"}


# --- get_datastream --------------------------------------------------------------------


def test_get_datastream_returns_public_datastream_for_anonymous(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)

    response = client.get(_detail_url(datastream.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(datastream.id)


def test_get_datastream_returns_404_for_private_datastream_when_outsider(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace, private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(datastream.id))

    assert response.status_code == 404


def test_get_datastream_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(datastream.id))

    assert response.status_code == 200


def test_get_datastream_returns_404_for_nonexistent_datastream(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- update_datastream -----------------------------------------------------------------


def test_update_datastream_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_update_datastream_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(datastream.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_datastream -----------------------------------------------------------------


def test_delete_datastream_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(datastream.id))

    assert response.status_code == 204
    assert client.get(_detail_url(datastream.id)).status_code == 404


def test_delete_datastream_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(datastream.id))

    assert response.status_code == 403


# --- get_datastream_tags / add / edit / remove ------------------------------------------


def test_get_datastream_tags_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    DatastreamTag.objects.create(datastream=datastream, key="season", value="summer")
    client.force_login(owner)

    response = client.get(_tags_url(datastream.id))

    assert response.status_code == 200
    assert {"key": "season", "value": "summer"} in response.json()


def test_get_datastream_tags_returns_404_for_private_datastream_when_outsider(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace, private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_tags_url(datastream.id))

    assert response.status_code == 404


def test_add_datastream_tag_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.post(
        _tags_url(datastream.id),
        data={"key": "season", "value": "summer"},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json() == {"key": "season", "value": "summer"}


def test_add_datastream_tag_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        _tags_url(datastream.id),
        data={"key": "season", "value": "summer"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_add_datastream_tag_returns_400_for_duplicate_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    DatastreamTag.objects.create(datastream=datastream, key="season", value="summer")
    client.force_login(owner)

    response = client.post(
        _tags_url(datastream.id),
        data={"key": "season", "value": "winter"},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_edit_datastream_tag_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    DatastreamTag.objects.create(datastream=datastream, key="season", value="summer")
    client.force_login(owner)

    response = client.put(
        _tags_url(datastream.id),
        data={"key": "season", "value": "winter"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["value"] == "winter"


def test_edit_datastream_tag_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    DatastreamTag.objects.create(datastream=datastream, key="season", value="summer")
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.put(
        _tags_url(datastream.id),
        data={"key": "season", "value": "winter"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_remove_datastream_tag_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    DatastreamTag.objects.create(datastream=datastream, key="season", value="summer")
    client.force_login(owner)

    response = client.delete(
        _tags_url(datastream.id),
        data={"key": "season"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not DatastreamTag.objects.filter(datastream=datastream, key="season").exists()


def test_remove_datastream_tag_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    DatastreamTag.objects.create(datastream=datastream, key="season", value="summer")
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(
        _tags_url(datastream.id),
        data={"key": "season"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_remove_datastream_tag_returns_404_for_unknown_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.delete(
        _tags_url(datastream.id),
        data={"key": "unknown"},
        content_type="application/json",
    )

    assert response.status_code == 404


# --- aggregate read endpoints (basic verification only) --------------------------------


def test_get_datastream_visualization_bootstrap_returns_public_datastream(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(
        workspace,
        aggregation_statistic="Mean",
        time_aggregation_interval=1,
        time_aggregation_interval_unit="days",
        unit=UnitFactory(workspace=workspace, symbol="cfs"),
    )

    response = client.get(f"{DATASTREAMS_URL}/visualization-bootstrap")

    assert response.status_code == 200
    body = response.json()
    returned_datastream = next(
        d for d in body["datastreams"] if d["id"] == str(datastream.id)
    )
    assert returned_datastream["aggregationStatistic"] == "Mean"
    assert returned_datastream["timeAggregationInterval"] == 1
    assert returned_datastream["timeAggregationIntervalUnit"] == "days"
    assert returned_datastream["unitSymbol"] == "cfs"


def test_get_datastream_tag_keys_returns_keys_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    DatastreamTag.objects.create(datastream=datastream, key="season", value="summer")
    client.force_login(owner)

    response = client.get(f"{DATASTREAMS_URL}/tags/keys")

    assert response.status_code == 200
    assert response.json()["season"] == ["summer"]


# --- get_datastream_csv ------------------------------------------------------------------


def test_get_datastream_csv_returns_csv_with_observations(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    ObservationFactory(datastream=datastream, result=12.5)

    response = client.get(f"{_detail_url(datastream.id)}/csv")

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    body = b"".join(response.streaming_content).decode()
    assert "12.5" in body
