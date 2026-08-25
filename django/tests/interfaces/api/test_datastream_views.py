import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.sta.models import (
    DatastreamAggregation,
    DatastreamStatus,
    LinkedResourceType,
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


def test_get_datastream_linked_resource_types_returns_registered_type_names(client):
    LinkedResourceType.objects.create(name="Photo")
    LinkedResourceType.objects.create(name="Report")

    response = client.get(f"{DATASTREAMS_URL}/linked-resource-types")

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


# --- update_datastream tags (PATCH merge semantics) -------------------------------------


def test_update_datastream_tags_adds_new_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    datastream.tags = {"season": "summer"}
    datastream.save()
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"tags": {"site": "upstream"}},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["tags"] == {"season": "summer", "site": "upstream"}


def test_update_datastream_tags_overwrites_existing_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    datastream.tags = {"season": "summer"}
    datastream.save()
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"tags": {"season": "winter"}},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["tags"] == {"season": "winter"}


def test_update_datastream_tags_removes_key_when_value_is_null(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    datastream.tags = {"season": "summer", "site": "upstream"}
    datastream.save()
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"tags": {"season": None}},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["tags"] == {"site": "upstream"}


def test_update_datastream_tags_ignores_null_for_missing_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    datastream.tags = {"season": "summer"}
    datastream.save()
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"tags": {"unknown": None}},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["tags"] == {"season": "summer"}


@pytest.mark.parametrize("value", [["summer"], {"nested": "value"}, 3, True])
def test_update_datastream_tags_returns_422_for_non_string_value(client, value):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"tags": {"season": value}},
        content_type="application/json",
    )

    assert response.status_code == 422


def test_update_datastream_tags_returns_422_for_empty_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"tags": {"": "summer"}},
        content_type="application/json",
    )

    assert response.status_code == 422


def test_update_datastream_tags_returns_422_for_empty_value(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"tags": {"season": ""}},
        content_type="application/json",
    )

    assert response.status_code == 422


def test_update_datastream_tags_locks_row_for_update(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as queries:
        client.patch(
            _detail_url(datastream.id),
            data={"tags": {"season": "summer"}},
            content_type="application/json",
        )

    assert any("FOR UPDATE" in query["sql"] for query in queries.captured_queries)


def test_update_datastream_without_tags_does_not_lock_row(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as queries:
        client.patch(
            _detail_url(datastream.id),
            data={"name": "Updated Name"},
            content_type="application/json",
        )

    assert not any("FOR UPDATE" in query["sql"] for query in queries.captured_queries)


def test_update_datastream_tags_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    datastream.tags = {"season": "summer"}
    datastream.save()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(datastream.id),
        data={"tags": {"season": "winter"}},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_datastream_with_tags_succeeds(client):
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
        data=_datastream_body(
            monitoring_site, method, observed_property, processing_level, unit,
            tags={"season": "summer"},
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["tags"] == {"season": "summer"}


def test_create_datastream_returns_422_for_null_tag_value(client):
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
        data=_datastream_body(
            monitoring_site, method, observed_property, processing_level, unit,
            tags={"season": None},
        ),
        content_type="application/json",
    )

    assert response.status_code == 422


def test_create_datastream_returns_422_for_empty_tag_key(client):
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
        data=_datastream_body(
            monitoring_site, method, observed_property, processing_level, unit,
            tags={"": "summer"},
        ),
        content_type="application/json",
    )

    assert response.status_code == 422


def test_create_datastream_returns_422_for_empty_tag_value(client):
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
        data=_datastream_body(
            monitoring_site, method, observed_property, processing_level, unit,
            tags={"season": ""},
        ),
        content_type="application/json",
    )

    assert response.status_code == 422


# --- removed tag sub-resource endpoints ---------------------------------------------


@pytest.mark.parametrize("method", ["get", "post", "put", "delete"])
def test_datastream_tags_sub_resource_is_removed(client, method):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = getattr(client, method)(
        _tags_url(datastream.id),
        data={"key": "season", "value": "summer"},
        content_type="application/json",
    )

    assert response.status_code == 404


# --- aggregate read endpoints (basic verification only) --------------------------------


def test_get_datastream_visualization_bootstrap_returns_public_datastream(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)

    response = client.get(f"{DATASTREAMS_URL}/visualization-bootstrap")

    assert response.status_code == 200
    body = response.json()
    assert str(datastream.id) in [d["id"] for d in body["datastreams"]]


def test_get_datastream_tag_keys_returns_keys_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    datastream.tags = {"season": "summer"}
    datastream.save()
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
