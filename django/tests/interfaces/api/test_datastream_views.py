import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.sta.models import Datastream, DatastreamLinkedResource
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
    SampledMediumFactory,
    AggregationStatisticFactory,
    DatastreamStatusFactory,
)

pytestmark = pytest.mark.django_db

DATASTREAMS_COLLECTION_URL = "/api/ogc/collections/datastreams"
DATASTREAMS_URL = f"{DATASTREAMS_COLLECTION_URL}/items"


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
    assert str(datastream.id) in [d["id"] for d in response.json()["data"]]


def test_get_datastreams_excludes_private_datastream_for_outsider(client):
    workspace = WorkspaceFactory()
    _make_datastream(workspace, private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(DATASTREAMS_URL)

    assert response.json()["data"] == []


def test_get_datastreams_includes_private_datastream_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace, private=True)
    client.force_login(owner)

    response = client.get(DATASTREAMS_URL)

    assert response.status_code == 200
    assert str(datastream.id) in [d["id"] for d in response.json()["data"]]


def test_get_datastreams_returns_400_for_malformed_tag(client):
    response = client.get(DATASTREAMS_URL, {"tag": "no-colon-in-here"})

    assert response.status_code == 400


# --- full-text search (q) ------------------------------------------------------------


def test_get_datastreams_q_matches_tag_value(client):
    workspace = WorkspaceFactory()
    match = _make_datastream(workspace, name="Datastream A", tags={"season": "summer"})
    _make_datastream(workspace, name="Datastream B", tags={})

    response = client.get(DATASTREAMS_URL, {"q": "summer"})

    assert response.status_code == 200
    assert {d["id"] for d in response.json()["data"]} == {str(match.id)}


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
    assert set(response.json().keys()) == {"id"}
    detail = client.get(_detail_url(response.json()["id"]))
    assert detail.json()["data"]["name"] == "New Datastream"


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


def test_create_datastream_returns_400_for_nonexistent_observed_property(client):
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
            monitoring_site,
            method,
            observed_property,
            processing_level,
            unit,
            observedPropertyId=str(uuid.uuid4()),
        ),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_datastream_returns_400_for_observed_property_from_another_workspace(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    other_workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    method = MethodFactory(workspace=workspace)
    observed_property = ObservedPropertyFactory(workspace=other_workspace)
    processing_level = ProcessingLevelFactory(workspace=workspace)
    unit = UnitFactory(workspace=workspace)
    client.force_login(owner)

    response = client.post(
        DATASTREAMS_URL,
        data=_datastream_body(monitoring_site, method, observed_property, processing_level, unit),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_datastream --------------------------------------------------------------------


def test_get_datastream_returns_public_datastream_for_anonymous(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)

    response = client.get(_detail_url(datastream.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(datastream.id)


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

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(datastream.id))
    assert detail.json()["data"]["name"] == "Updated Name"


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


def test_update_datastream_returns_400_for_unit_from_another_workspace(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    other_workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    other_unit = UnitFactory(workspace=other_workspace)
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"unitId": str(other_unit.id)},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_update_datastream_returns_400_for_monitoring_site_from_another_workspace(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    other_workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    other_monitoring_site = MonitoringSiteFactory(workspace=other_workspace)
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"monitoringSiteId": str(other_monitoring_site.id)},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_update_datastream_succeeds_with_monitoring_site_in_same_workspace(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    other_monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"monitoringSiteId": str(other_monitoring_site.id)},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(datastream.id))
    assert detail.json()["data"]["monitoringSiteId"] == str(other_monitoring_site.id)


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

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(datastream.id))
    assert detail.json()["data"]["tags"] == {"season": "summer", "site": "upstream"}


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

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(datastream.id))
    assert detail.json()["data"]["tags"] == {"season": "winter"}


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

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(datastream.id))
    assert detail.json()["data"]["tags"] == {"site": "upstream"}


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

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(datastream.id))
    assert detail.json()["data"]["tags"] == {"season": "summer"}


@pytest.mark.parametrize("value", [["summer"], {"nested": "value"}, 3, True])
def test_update_datastream_tags_returns_400_for_non_string_value(client, value):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"tags": {"season": value}},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_update_datastream_tags_returns_400_for_empty_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"tags": {"": "summer"}},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_update_datastream_tags_returns_400_for_empty_value(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.patch(
        _detail_url(datastream.id),
        data={"tags": {"season": ""}},
        content_type="application/json",
    )

    assert response.status_code == 400


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
    detail = client.get(_detail_url(response.json()["id"]))
    assert detail.json()["data"]["tags"] == {"season": "summer"}


def test_create_datastream_returns_400_for_null_tag_value(client):
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

    assert response.status_code == 400


def test_create_datastream_returns_400_for_empty_tag_key(client):
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

    assert response.status_code == 400


def test_create_datastream_returns_400_for_empty_tag_value(client):
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

    assert response.status_code == 400


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
    datastream = _make_datastream(
        workspace,
        aggregation_statistic="Mean",
        method=MethodFactory(workspace=workspace, name="Shielded sensor"),
        time_aggregation_interval=1,
        time_aggregation_interval_unit="days",
        unit=UnitFactory(
            workspace=workspace, name="Cubic feet per second", symbol="cfs"
        ),
    )

    response = client.get(f"{DATASTREAMS_COLLECTION_URL}/visualization-bootstrap")

    assert response.status_code == 200
    body = response.json()
    returned_datastream = next(
        d for d in body["datastreams"] if d["id"] == str(datastream.id)
    )
    assert returned_datastream["aggregationStatistic"] == "Mean"
    assert returned_datastream["methodName"] == "Shielded sensor"
    assert returned_datastream["timeAggregationInterval"] == 1
    assert returned_datastream["timeAggregationIntervalUnit"] == "days"
    assert returned_datastream["unitName"] == "Cubic feet per second"
    assert returned_datastream["unitSymbol"] == "cfs"


def test_get_datastream_tag_keys_returns_keys_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    datastream.tags = {"season": "summer"}
    datastream.save()
    client.force_login(owner)

    response = client.get(f"{DATASTREAMS_COLLECTION_URL}/tags/keys")

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


# --- linked resources ----------------------------------------------------------------


def _linked_resources_url(datastream_id):
    return f"{_detail_url(datastream_id)}/linked-resources"


def _make_datastream_linked_resources(owner, names):
    workspace = WorkspaceFactory(owner=owner)
    parent = _make_datastream(workspace)
    for name in names:
        DatastreamLinkedResource.objects.create(datastream=parent, name=name, type="Report", url=f"https://example.com/{name}")
    return parent


def test_get_datastream_linked_resources_pages_by_name(client):
    owner = UserFactory()
    parent = _make_datastream_linked_resources(owner, ["C", "A", "B"])
    client.force_login(owner)

    first = client.get(_linked_resources_url(parent.id), {"limit": 2}).json()
    second = client.get(_linked_resources_url(parent.id), {"limit": 2, "offset": 2}).json()

    assert [item["name"] for item in first["data"]] == ["A", "B"]
    assert first["meta"] == {"limit": 2, "offset": 0, "totalCount": 3}
    assert "next" in [link["rel"] for link in first["links"]]
    assert [item["name"] for item in second["data"]] == ["C"]


def test_get_datastream_linked_resources_selects_properties(client):
    owner = UserFactory()
    parent = _make_datastream_linked_resources(owner, ["A"])
    client.force_login(owner)

    response = client.get(_linked_resources_url(parent.id), {"properties": "name"})

    assert response.json()["data"] == [{"name": "A"}]


def test_get_datastream_linked_resources_rejects_include(client):
    owner = UserFactory()
    parent = _make_datastream_linked_resources(owner, ["A"])
    client.force_login(owner)

    response = client.get(_linked_resources_url(parent.id), {"include": "datastream"})

    assert response.status_code == 400


def test_get_datastream_linked_resource_returns_item(client):
    owner = UserFactory()
    parent = _make_datastream_linked_resources(owner, ["A", "B"])
    linked_resource = DatastreamLinkedResource.objects.get(datastream=parent, name="B")
    client.force_login(owner)

    response = client.get(f"{_linked_resources_url(parent.id)}/{linked_resource.id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(linked_resource.id)
    assert data["name"] == "B"
    assert data["type"] == "Report"
    assert data["link"] == "https://example.com/B"


def test_get_datastream_linked_resource_returns_404_for_unknown_id(client):
    owner = UserFactory()
    parent = _make_datastream_linked_resources(owner, ["A"])
    client.force_login(owner)

    response = client.get(f"{_linked_resources_url(parent.id)}/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_datastream_linked_resource_returns_404_for_other_parents_resource(client):
    owner = UserFactory()
    parent = _make_datastream_linked_resources(owner, ["A"])
    other_parent = _make_datastream_linked_resources(owner, ["B"])
    other_resource = DatastreamLinkedResource.objects.get(datastream=other_parent)
    client.force_login(owner)

    response = client.get(f"{_linked_resources_url(parent.id)}/{other_resource.id}")

    assert response.status_code == 404


def test_get_datastream_linked_resource_returns_404_for_private_parent_when_outsider(client):
    parent = _make_datastream(WorkspaceFactory(), private=True)
    linked_resource = DatastreamLinkedResource.objects.create(
        datastream=parent, name="A", type="Report", url="https://example.com/A"
    )
    client.force_login(UserFactory())

    response = client.get(f"{_linked_resources_url(parent.id)}/{linked_resource.id}")

    assert response.status_code == 404


def test_add_datastream_linked_resource_succeeds_with_link(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.post(
        _linked_resources_url(datastream.id),
        data={
            "name": "Datastream Report",
            "type": "Report",
            "link": "https://example.com/report.pdf",
        },
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}
    linked_resources = client.get(_linked_resources_url(datastream.id)).json()["data"]
    assert linked_resources[0]["name"] == "Datastream Report"


def test_add_datastream_linked_resource_returns_400_for_duplicate_name(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)
    client.post(
        _linked_resources_url(datastream.id),
        data={"name": "Datastream Report", "type": "Report", "link": "https://example.com/a.pdf"},
    )

    response = client.post(
        _linked_resources_url(datastream.id),
        data={"name": "Datastream Report", "type": "Report", "link": "https://example.com/b.pdf"},
    )

    assert response.status_code == 400


# --- include / properties ---------------------------------------------------------


def test_get_datastream_include_sideloads_all_six_relations(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.get(
        _detail_url(datastream.id),
        {
            "include": "workspace,monitoringSite,method,observedProperty,processingLevel,unit"
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(datastream.id)
    included = body["included"]
    assert {row["id"] for row in included["workspaces"]} == {str(workspace.id)}
    assert {row["id"] for row in included["monitoringSites"]} == {
        str(datastream.monitoring_site_id)
    }
    assert {row["id"] for row in included["methods"]} == {str(datastream.method_id)}
    assert {row["id"] for row in included["observedProperties"]} == {
        str(datastream.observed_property_id)
    }
    assert {row["id"] for row in included["processingLevels"]} == {
        str(datastream.processing_level_id)
    }
    assert {row["id"] for row in included["units"]} == {str(datastream.unit_id)}


def test_get_datastream_include_sideloads_vocabulary_fields(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    sampled_medium = SampledMediumFactory(name="Surface Water")
    aggregation_statistic = AggregationStatisticFactory(name="Maximum")
    status = DatastreamStatusFactory(name="Active")
    datastream = _make_datastream(
        workspace,
        sampled_medium=sampled_medium.name,
        aggregation_statistic=aggregation_statistic.name,
        status=status.name,
    )
    client.force_login(owner)

    response = client.get(
        _detail_url(datastream.id),
        {"include": "sampledMedium,aggregationStatistic,status"},
    )

    assert response.status_code == 200
    included = response.json()["included"]
    assert {row["id"] for row in included["sampledMediums"]} == {str(sampled_medium.id)}
    assert {row["id"] for row in included["aggregationStatistics"]} == {
        str(aggregation_statistic.id)
    }
    assert {row["id"] for row in included["datastreamStatuses"]} == {str(status.id)}


def test_get_datastream_include_status_omits_bucket_when_status_unset(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace, status=None)
    client.force_login(owner)

    response = client.get(_detail_url(datastream.id), {"include": "status"})

    assert response.status_code == 200
    assert "datastreamStatuses" not in response.json().get("included", {})


def test_get_datastreams_include_vocabulary_field_deduplicates_across_items(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    sampled_medium = SampledMediumFactory(name="Groundwater")
    _make_datastream(workspace, sampled_medium=sampled_medium.name)
    _make_datastream(workspace, sampled_medium=sampled_medium.name)
    client.force_login(owner)

    response = client.get(DATASTREAMS_URL, {"include": "sampledMedium"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert [row["id"] for row in body["included"]["sampledMediums"]] == [
        str(sampled_medium.id)
    ]


def test_get_datastream_without_include_omits_included_bucket(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(datastream.id))

    assert response.status_code == 200
    body = response.json()
    assert not body.get("included")


def test_get_datastreams_include_does_not_scale_queries_with_datastream_count(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    for _ in range(5):
        _make_datastream(workspace)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(
            DATASTREAMS_URL,
            {
                "include": "workspace,monitoringSite,method,observedProperty,processingLevel,unit"
            },
        )

    for _ in range(5):
        _make_datastream(workspace)

    with CaptureQueriesContext(connection) as large:
        client.get(
            DATASTREAMS_URL,
            {
                "include": "workspace,monitoringSite,method,observedProperty,processingLevel,unit"
            },
        )

    assert len(large.captured_queries) == len(small.captured_queries)


def test_get_datastreams_properties_filters_response_fields(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    _make_datastream(workspace)
    client.force_login(owner)

    response = client.get(DATASTREAMS_URL, {"properties": "id,name"})

    assert response.status_code == 200
    row = response.json()["data"][0]
    assert set(row.keys()) == {"id", "name"}


# --- bbox --------------------------------------------------------------------------------


def _datastream_at(longitude, latitude):
    return DatastreamFactory(monitoring_site=MonitoringSiteFactory(longitude=longitude, latitude=latitude))


def _datastream_ids(response):
    return {datastream["id"] for datastream in response.json()["data"]}


def test_get_datastreams_filters_by_monitoring_site_location(client):
    inside = _datastream_at(-111.5, 40.5)
    _datastream_at(-100, 40.5)

    response = client.get(DATASTREAMS_URL, {"bbox": "-112,40,-111,41"})

    assert response.status_code == 200
    assert _datastream_ids(response) == {str(inside.id)}


def test_get_datastreams_filters_by_a_bbox_crossing_the_antimeridian(client):
    east = _datastream_at(175, -15)
    west = _datastream_at(-175, -15)
    _datastream_at(0, -15)

    response = client.get(DATASTREAMS_URL, {"bbox": "170,-20,-170,-10"})

    assert response.status_code == 200
    assert _datastream_ids(response) == {str(east.id), str(west.id)}


def test_get_datastreams_combines_bbox_with_other_filters(client):
    inside = _datastream_at(-111.5, 40.5)
    _datastream_at(-111.5, 40.5)

    response = client.get(
        DATASTREAMS_URL, {"bbox": "-112,40,-111,41", "monitoringSiteId": str(inside.monitoring_site_id)}
    )

    assert response.status_code == 200
    assert _datastream_ids(response) == {str(inside.id)}


def test_get_datastreams_returns_400_for_invalid_bbox(client):
    response = client.get(DATASTREAMS_URL, {"bbox": "-112,40,-111,91"})

    assert response.status_code == 400


# --- datetime ----------------------------------------------------------------------------


def _datastream_spanning(begin, end):
    return DatastreamFactory(phenomenon_begin_time=begin, phenomenon_end_time=end)


def test_get_datastreams_filters_by_overlapping_phenomenon_time(client):
    jan = timezone.now().replace(microsecond=0) - timedelta(days=60)
    feb = jan + timedelta(days=30)
    before = _datastream_spanning(jan - timedelta(days=20), jan - timedelta(days=10))
    overlaps_start = _datastream_spanning(jan - timedelta(days=5), jan + timedelta(days=5))
    inside = _datastream_spanning(jan + timedelta(days=1), jan + timedelta(days=2))
    touches_end = _datastream_spanning(feb, feb + timedelta(days=5))
    after = _datastream_spanning(feb + timedelta(days=1), feb + timedelta(days=5))

    response = client.get(DATASTREAMS_URL, {"datetime": f"{jan.isoformat()}/{feb.isoformat()}"})

    assert response.status_code == 200
    ids = _datastream_ids(response)
    assert {str(overlaps_start.id), str(inside.id), str(touches_end.id)} <= ids
    assert not ids & {str(before.id), str(after.id)}


def test_get_datastreams_datetime_matches_datastreams_without_observations(client):
    empty = _datastream_spanning(None, None)
    old = _datastream_spanning(timezone.now() - timedelta(days=20), timezone.now() - timedelta(days=10))

    response = client.get(DATASTREAMS_URL, {"datetime": timezone.now().replace(microsecond=0).isoformat()})

    assert response.status_code == 200
    assert str(empty.id) in _datastream_ids(response)
    assert str(old.id) not in _datastream_ids(response)


def test_get_datastreams_returns_400_for_invalid_datetime(client):
    response = client.get(DATASTREAMS_URL, {"datetime": "../.."})

    assert response.status_code == 400


# --- server-maintained statistics -------------------------------------------------------

STATISTICS = {
    "valueCount": 42,
    "phenomenonBeginTime": "2020-01-01T00:00:00Z",
    "phenomenonEndTime": "2020-12-31T00:00:00Z",
    "resultBeginTime": "2020-01-01T00:00:00Z",
    "resultEndTime": "2020-12-31T00:00:00Z",
}


def test_create_datastream_ignores_server_maintained_statistics(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    body = _datastream_body(
        MonitoringSiteFactory(workspace=workspace),
        MethodFactory(workspace=workspace),
        ObservedPropertyFactory(workspace=workspace),
        ProcessingLevelFactory(workspace=workspace),
        UnitFactory(workspace=workspace),
        **STATISTICS,
    )
    client.force_login(owner)

    response = client.post(DATASTREAMS_URL, data=body, content_type="application/json")

    assert response.status_code == 201
    datastream = Datastream.objects.get(pk=response.json()["id"])
    assert datastream.value_count in (None, 0)
    assert datastream.phenomenon_begin_time is None
    assert datastream.phenomenon_end_time is None
    assert datastream.result_begin_time is None


def test_update_datastream_ignores_server_maintained_statistics(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    begin = timezone.now().replace(microsecond=0) - timedelta(days=2)
    datastream = DatastreamFactory(
        monitoring_site=MonitoringSiteFactory(workspace=workspace),
        value_count=3,
        phenomenon_begin_time=begin,
        phenomenon_end_time=begin + timedelta(days=1),
    )
    client.force_login(owner)

    response = client.patch(_detail_url(datastream.id), data=STATISTICS, content_type="application/json")

    assert response.status_code == 204
    datastream.refresh_from_db()
    assert datastream.value_count == 3
    assert datastream.phenomenon_begin_time == begin
    assert datastream.phenomenon_end_time == begin + timedelta(days=1)


def test_get_datastream_returns_server_maintained_statistics(client):
    begin = timezone.now().replace(microsecond=0) - timedelta(days=2)
    datastream = DatastreamFactory(value_count=3, phenomenon_begin_time=begin, phenomenon_end_time=begin)

    response = client.get(_detail_url(datastream.id), {"properties": "valueCount,phenomenonBeginTime"})

    assert response.status_code == 200
    assert response.json()["data"] == {"valueCount": 3, "phenomenonBeginTime": begin.isoformat()}


def test_datastream_request_bodies_do_not_declare_server_maintained_statistics():
    from interfaces.api.urls import api

    schemas = api.get_openapi_schema(path_prefix="/api/ogc/")["components"]["schemas"]

    for body in ("DatastreamPostBody", "DatastreamPatchBody"):
        assert not set(schemas[body]["properties"]) & set(STATISTICS)
    assert set(STATISTICS) <= set(schemas["DatastreamResponse"]["properties"])
