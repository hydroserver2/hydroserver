import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.test.utils import CaptureQueriesContext

from core.sta.models import MonitoringSiteLinkedResource
from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory, MonitoringSiteTypeFactory

pytestmark = pytest.mark.django_db

MONITORING_SITES_COLLECTION_URL = "/api/ogc/collections/monitoring-sites"
MONITORING_SITES_URL = f"{MONITORING_SITES_COLLECTION_URL}/items"


def _detail_url(monitoring_site_id):
    return f"{MONITORING_SITES_URL}/{monitoring_site_id}"


def _tags_url(monitoring_site_id):
    return f"{_detail_url(monitoring_site_id)}/tags"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="MonitoringSite", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _monitoring_site_body(workspace_id, **overrides):
    body = {
        "name": "New Monitoring Site",
        "description": "A new site.",
        "code": "SITE-NEW",
        "type": "Stream",
        "latitude": 40.0,
        "longitude": -111.0,
        "isPrivate": False,
        "workspaceId": str(workspace_id),
    }
    body.update(overrides)
    return body


# --- get_monitoring_sites -----------------------------------------------------------------


def test_get_monitoring_sites_includes_public_monitoring_site_for_anonymous(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)

    response = client.get(MONITORING_SITES_URL)

    assert response.status_code == 200
    assert str(monitoring_site.id) in [t["id"] for t in response.json()["data"]]


def test_get_monitoring_sites_excludes_private_monitoring_site_for_outsider(client):
    workspace = WorkspaceFactory()
    MonitoringSiteFactory(workspace=workspace, private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(MONITORING_SITES_URL)

    assert response.json()["data"] == []


def test_get_monitoring_sites_includes_private_monitoring_site_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace, private=True)
    client.force_login(owner)

    response = client.get(MONITORING_SITES_URL)

    assert response.status_code == 200
    assert str(monitoring_site.id) in [t["id"] for t in response.json()["data"]]


def test_get_monitoring_sites_returns_400_for_malformed_bbox(client):
    response = client.get(MONITORING_SITES_URL, {"bbox": "not,a,valid,bbox"})

    assert response.status_code == 400


@pytest.mark.parametrize(
    "bbox",
    ["-181,40,-111,41", "-112,-91,-111,41", "-112,41,-111,40", "-112,40,-111", "-112,40,100,-111,41,0"],
)
def test_get_monitoring_sites_returns_400_for_invalid_bbox(client, bbox):
    response = client.get(MONITORING_SITES_URL, {"bbox": bbox})

    assert response.status_code == 400


def _site_ids(response):
    return {site["id"] for site in response.json()["data"]}


def test_get_monitoring_sites_filters_by_bbox(client):
    inside = MonitoringSiteFactory(longitude=-111.5, latitude=40.5)
    MonitoringSiteFactory(longitude=-100, latitude=40.5)

    response = client.get(MONITORING_SITES_URL, {"bbox": "-112,40,-111,41"})

    assert response.status_code == 200
    assert _site_ids(response) == {str(inside.id)}


def test_get_monitoring_sites_accepts_a_six_value_bbox_and_ignores_heights(client):
    inside = MonitoringSiteFactory(longitude=-111.5, latitude=40.5, elevation_m=5000)
    MonitoringSiteFactory(longitude=-100, latitude=40.5)

    response = client.get(MONITORING_SITES_URL, {"bbox": "-112,40,0,-111,41,10"})

    assert response.status_code == 200
    assert _site_ids(response) == {str(inside.id)}


def test_get_monitoring_sites_filters_by_a_bbox_crossing_the_antimeridian(client):
    east = MonitoringSiteFactory(longitude=175, latitude=-15)
    west = MonitoringSiteFactory(longitude=-175, latitude=-15)
    MonitoringSiteFactory(longitude=0, latitude=-15)

    response = client.get(MONITORING_SITES_URL, {"bbox": "170,-20,-170,-10"})

    assert response.status_code == 200
    assert _site_ids(response) == {str(east.id), str(west.id)}


# --- datetime ----------------------------------------------------------------------------
#
# A site's time is the observed time of each of its datastreams the requester can view. It
# matches a datetime when one of those datastreams overlaps it, or when none of them has
# observations (no time matches any datetime, per OGC API - Features Core Req 26C).


def _observed_datastream(monitoring_site, begin, end, **kwargs):
    return DatastreamFactory(
        monitoring_site=monitoring_site,
        phenomenon_begin_time=begin,
        phenomenon_end_time=end,
        **kwargs,
    )


def test_get_monitoring_sites_datetime_matches_sites_with_an_overlapping_datastream(client):
    overlapping = MonitoringSiteFactory()
    _observed_datastream(overlapping, "2024-01-01T00:00:00Z", "2024-03-01T00:00:00Z")
    touching = MonitoringSiteFactory()
    _observed_datastream(touching, "2024-03-01T00:00:00Z", "2024-04-01T00:00:00Z")
    before = MonitoringSiteFactory()
    _observed_datastream(before, "2023-01-01T00:00:00Z", "2023-02-01T00:00:00Z")

    response = client.get(
        MONITORING_SITES_URL, {"datetime": "2024-02-01T00:00:00Z/2024-03-01T00:00:00Z"}
    )

    assert response.status_code == 200
    assert _site_ids(response) == {str(overlapping.id), str(touching.id)}


def test_get_monitoring_sites_datetime_requires_one_datastream_to_overlap(client):
    # Neither datastream has observations in March, even though the site's overall span does.
    site = MonitoringSiteFactory()
    _observed_datastream(site, "2024-01-01T00:00:00Z", "2024-02-01T00:00:00Z")
    _observed_datastream(site, "2024-06-01T00:00:00Z", "2024-07-01T00:00:00Z")

    march = client.get(MONITORING_SITES_URL, {"datetime": "2024-03-01T00:00:00Z/2024-03-31T00:00:00Z"})
    june = client.get(MONITORING_SITES_URL, {"datetime": "2024-06-15T00:00:00Z"})

    assert str(site.id) not in _site_ids(march)
    assert str(site.id) in _site_ids(june)


@pytest.mark.parametrize(
    "datetime_value, expected",
    [
        ("2024-06-01T00:00:00Z/..", {"later"}),
        ("../2024-01-31T00:00:00Z", {"earlier"}),
        ("2024-06-01T00:00:00Z/", {"later"}),
    ],
)
def test_get_monitoring_sites_datetime_accepts_half_bounded_intervals(client, datetime_value, expected):
    sites = {
        "earlier": MonitoringSiteFactory(),
        "later": MonitoringSiteFactory(),
    }
    _observed_datastream(sites["earlier"], "2024-01-01T00:00:00Z", "2024-02-01T00:00:00Z")
    _observed_datastream(sites["later"], "2024-06-01T00:00:00Z", "2024-07-01T00:00:00Z")

    response = client.get(MONITORING_SITES_URL, {"datetime": datetime_value})

    assert response.status_code == 200
    assert _site_ids(response) == {str(sites[name].id) for name in expected}


def test_get_monitoring_sites_datetime_matches_sites_without_observed_datastreams(client):
    without_datastreams = MonitoringSiteFactory()
    without_observations = MonitoringSiteFactory()
    DatastreamFactory(monitoring_site=without_observations)

    response = client.get(MONITORING_SITES_URL, {"datetime": "2024-02-01T00:00:00Z"})

    assert _site_ids(response) == {str(without_datastreams.id), str(without_observations.id)}


def test_get_monitoring_sites_datetime_ignores_private_datastreams_the_requester_cannot_view(client):
    # A private datastream that overlaps must not make the site match...
    hidden_overlap = MonitoringSiteFactory()
    _observed_datastream(hidden_overlap, "2023-01-01T00:00:00Z", "2023-02-01T00:00:00Z")
    _observed_datastream(hidden_overlap, "2024-01-01T00:00:00Z", "2024-03-01T00:00:00Z", private=True)
    # ...and a site whose only observed datastream is private has no visible time, so it matches.
    only_private = MonitoringSiteFactory()
    _observed_datastream(only_private, "2023-01-01T00:00:00Z", "2023-02-01T00:00:00Z", private=True)

    response = client.get(MONITORING_SITES_URL, {"datetime": "2024-02-01T00:00:00Z"})

    assert str(hidden_overlap.id) not in _site_ids(response)
    assert str(only_private.id) in _site_ids(response)


def test_get_monitoring_sites_datetime_uses_private_datastreams_the_owner_can_view(client):
    owner = UserFactory()
    site = MonitoringSiteFactory(workspace=WorkspaceFactory(owner=owner))
    _observed_datastream(site, "2024-01-01T00:00:00Z", "2024-03-01T00:00:00Z", private=True)
    client.force_login(owner)

    overlapping = client.get(MONITORING_SITES_URL, {"datetime": "2024-02-01T00:00:00Z"})
    elsewhere = client.get(MONITORING_SITES_URL, {"datetime": "2020-01-01T00:00:00Z"})

    assert str(site.id) in _site_ids(overlapping)
    assert str(site.id) not in _site_ids(elsewhere)


def test_get_monitoring_sites_datetime_combines_with_bbox(client):
    inside = MonitoringSiteFactory(longitude=-111.5, latitude=40.5)
    _observed_datastream(inside, "2024-01-01T00:00:00Z", "2024-03-01T00:00:00Z")
    inside_elsewhen = MonitoringSiteFactory(longitude=-111.5, latitude=40.5)
    _observed_datastream(inside_elsewhen, "2020-01-01T00:00:00Z", "2020-03-01T00:00:00Z")
    outside = MonitoringSiteFactory(longitude=-100, latitude=40.5)
    _observed_datastream(outside, "2024-01-01T00:00:00Z", "2024-03-01T00:00:00Z")

    response = client.get(
        MONITORING_SITES_URL, {"bbox": "-112,40,-111,41", "datetime": "2024-02-01T00:00:00Z"}
    )

    assert _site_ids(response) == {str(inside.id)}


def test_get_monitoring_sites_returns_400_for_invalid_datetime(client):
    response = client.get(MONITORING_SITES_URL, {"datetime": "2024-02-01"})

    assert response.status_code == 400


def test_get_monitoring_sites_returns_400_for_malformed_tag(client):
    response = client.get(MONITORING_SITES_URL, {"tag": "no-colon-in-here"})

    assert response.status_code == 400


# --- full-text search (q) ------------------------------------------------------------


def test_get_monitoring_sites_q_matches_name(client):
    workspace = WorkspaceFactory()
    match = MonitoringSiteFactory(
        workspace=workspace, name="Zephyrsite Creek", description="A creek site.", type="Stream"
    )
    MonitoringSiteFactory(
        workspace=workspace, name="Unrelated Site", description="Nothing to do with it.", type="Stream"
    )

    response = client.get(MONITORING_SITES_URL, {"q": "Zephyrsite"})

    assert response.status_code == 200
    assert {s["id"] for s in response.json()["data"]} == {str(match.id)}


def test_get_monitoring_sites_q_matches_type_field(client):
    workspace = WorkspaceFactory()
    match = MonitoringSiteFactory(
        workspace=workspace, name="Site A", description="desc a", type="Groundwater Well"
    )
    MonitoringSiteFactory(workspace=workspace, name="Site B", description="desc b", type="Stream")

    response = client.get(MONITORING_SITES_URL, {"q": "Groundwater"})

    assert {s["id"] for s in response.json()["data"]} == {str(match.id)}


def test_get_monitoring_sites_q_matches_tag_value(client):
    workspace = WorkspaceFactory()
    match = MonitoringSiteFactory(
        workspace=workspace, name="Site A", type="Stream", tags={"season": "summer"}
    )
    MonitoringSiteFactory(workspace=workspace, name="Site B", type="Stream", tags={})

    response = client.get(MONITORING_SITES_URL, {"q": "summer"})

    assert {s["id"] for s in response.json()["data"]} == {str(match.id)}


def test_get_monitoring_sites_q_comma_separated_terms_are_or(client):
    workspace = WorkspaceFactory()
    site_a = MonitoringSiteFactory(workspace=workspace, name="Alphasite", type="Stream")
    site_b = MonitoringSiteFactory(workspace=workspace, name="Betasite", type="Stream")
    MonitoringSiteFactory(workspace=workspace, name="Gammasite", type="Stream")

    response = client.get(MONITORING_SITES_URL, {"q": "Alphasite, Betasite"})

    assert {s["id"] for s in response.json()["data"]} == {str(site_a.id), str(site_b.id)}


def test_get_monitoring_sites_q_whitespace_separated_terms_are_and(client):
    workspace = WorkspaceFactory()
    match = MonitoringSiteFactory(workspace=workspace, name="Redfish Creek", type="Stream")
    MonitoringSiteFactory(workspace=workspace, name="Redfish Lake", type="Stream")

    response = client.get(MONITORING_SITES_URL, {"q": "Redfish Creek"})

    assert {s["id"] for s in response.json()["data"]} == {str(match.id)}


def test_get_monitoring_sites_q_is_case_insensitive(client):
    workspace = WorkspaceFactory()
    match = MonitoringSiteFactory(workspace=workspace, name="Zephyrsite Creek", type="Stream")

    response = client.get(MONITORING_SITES_URL, {"q": "ZEPHYRSITE"})

    assert {s["id"] for s in response.json()["data"]} == {str(match.id)}


def test_get_monitoring_sites_q_orders_by_relevance_by_default(client):
    workspace = WorkspaceFactory()
    name_match = MonitoringSiteFactory(workspace=workspace, name="Willowbrook", type="Stream")
    description_match = MonitoringSiteFactory(
        workspace=workspace,
        name="Other Site",
        description="Willowbrook mentioned here",
        type="Stream",
    )

    response = client.get(MONITORING_SITES_URL, {"q": "Willowbrook"})

    ids = [s["id"] for s in response.json()["data"]]
    assert ids == [str(name_match.id), str(description_match.id)]


def test_get_monitoring_sites_user_sortby_takes_precedence_over_relevance(client):
    workspace = WorkspaceFactory()
    name_match = MonitoringSiteFactory(workspace=workspace, name="Bravo Fernwood", type="Stream")
    description_match = MonitoringSiteFactory(
        workspace=workspace,
        name="Alpha Site",
        description="Fernwood mentioned",
        type="Stream",
    )

    response = client.get(MONITORING_SITES_URL, {"q": "Fernwood", "sortby": "name"})

    names = [s["name"] for s in response.json()["data"]]
    assert names == [description_match.name, name_match.name]


def test_get_monitoring_sites_empty_q_does_not_filter(client):
    workspace = WorkspaceFactory()
    MonitoringSiteFactory(workspace=workspace, name="Site A", type="Stream")
    MonitoringSiteFactory(workspace=workspace, name="Site B", type="Stream")

    without_q = client.get(MONITORING_SITES_URL)
    with_empty_q = client.get(MONITORING_SITES_URL, {"q": ""})

    assert without_q.json()["meta"]["totalCount"] == with_empty_q.json()["meta"]["totalCount"] == 2


# --- create_monitoring_site ------------------------------------------------------------------


def test_create_monitoring_site_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        MONITORING_SITES_URL,
        data=_monitoring_site_body(workspace.id),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}
    detail = client.get(_detail_url(response.json()["id"]))
    assert detail.json()["data"]["name"] == "New Monitoring Site"


def test_create_monitoring_site_succeeds_with_non_terminating_binary_coordinates(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        MONITORING_SITES_URL,
        data=_monitoring_site_body(
            workspace.id, latitude=41.7501, longitude=-111.8102, elevationM=1380.45
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    detail = client.get(_detail_url(response.json()["id"]))
    assert detail.json()["data"]["latitude"] == 41.7501
    assert detail.json()["data"]["longitude"] == -111.8102
    assert detail.json()["data"]["elevationM"] == 1380.45


def test_create_monitoring_site_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        MONITORING_SITES_URL,
        data=_monitoring_site_body(workspace.id),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_monitoring_site_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        MONITORING_SITES_URL,
        data=_monitoring_site_body(workspace.id),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_get_site_type_icons_returns_configured_icon_mappings(client):
    response = client.get(f"{MONITORING_SITES_COLLECTION_URL}/site-type-icons")

    assert response.status_code == 200
    icons = {entry["icon"] for entry in response.json()}
    assert "gauge" in icons


# --- get_monitoring_site -----------------------------------------------------------------------


def test_get_monitoring_site_returns_public_monitoring_site_for_anonymous(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)

    response = client.get(_detail_url(monitoring_site.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(monitoring_site.id)


def test_get_monitoring_site_returns_elevation_m_as_camel_case(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(
        workspace=workspace,
        elevation_m=1380,
    )

    response = client.get(_detail_url(monitoring_site.id))

    assert response.status_code == 200
    assert response.json()["data"]["elevationM"] == 1380
    assert "elevation_m" not in response.json()["data"]


def test_get_monitoring_sites_sorts_by_elevation(client):
    workspace = WorkspaceFactory()
    low = MonitoringSiteFactory(workspace=workspace, elevation_m=100)
    high = MonitoringSiteFactory(workspace=workspace, elevation_m=2000)

    response = client.get(
        MONITORING_SITES_URL,
        {"workspaceId": str(workspace.id), "sortby": "-elevationM", "properties": "id,elevationM"},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(high.id), str(low.id)]


def test_get_monitoring_site_returns_404_for_private_monitoring_site_when_outsider(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace, private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(monitoring_site.id))

    assert response.status_code == 404


def test_get_monitoring_site_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(monitoring_site.id))

    assert response.status_code == 200


def test_get_monitoring_site_returns_404_for_nonexistent_monitoring_site(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- update_monitoring_site --------------------------------------------------------------------


def test_update_monitoring_site_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(monitoring_site.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(monitoring_site.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_monitoring_site_succeeds_with_non_terminating_binary_coordinates(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.patch(
        _detail_url(monitoring_site.id),
        data={"latitude": 41.7501, "longitude": -111.8102},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(monitoring_site.id))
    assert detail.json()["data"]["latitude"] == 41.7501
    assert detail.json()["data"]["longitude"] == -111.8102


def test_update_monitoring_site_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(monitoring_site.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_monitoring_site --------------------------------------------------------------------


def test_delete_monitoring_site_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(monitoring_site.id))

    assert response.status_code == 204
    assert client.get(_detail_url(monitoring_site.id)).status_code == 404


def test_delete_monitoring_site_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(monitoring_site.id))

    assert response.status_code == 403


# --- update_monitoring_site tags (PATCH merge semantics) --------------------------------


def test_update_monitoring_site_tags_adds_new_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    monitoring_site.tags = {"season": "summer"}
    monitoring_site.save()
    client.force_login(owner)

    response = client.patch(
        _detail_url(monitoring_site.id),
        data={"tags": {"site": "upstream"}},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(monitoring_site.id))
    assert detail.json()["data"]["tags"] == {"season": "summer", "site": "upstream"}


def test_update_monitoring_site_tags_overwrites_existing_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    monitoring_site.tags = {"season": "summer"}
    monitoring_site.save()
    client.force_login(owner)

    response = client.patch(
        _detail_url(monitoring_site.id),
        data={"tags": {"season": "winter"}},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(monitoring_site.id))
    assert detail.json()["data"]["tags"] == {"season": "winter"}


def test_update_monitoring_site_tags_removes_key_when_value_is_null(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    monitoring_site.tags = {"season": "summer", "site": "upstream"}
    monitoring_site.save()
    client.force_login(owner)

    response = client.patch(
        _detail_url(monitoring_site.id),
        data={"tags": {"season": None}},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(monitoring_site.id))
    assert detail.json()["data"]["tags"] == {"site": "upstream"}


def test_update_monitoring_site_tags_ignores_null_for_missing_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    monitoring_site.tags = {"season": "summer"}
    monitoring_site.save()
    client.force_login(owner)

    response = client.patch(
        _detail_url(monitoring_site.id),
        data={"tags": {"unknown": None}},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content
    detail = client.get(_detail_url(monitoring_site.id))
    assert detail.json()["data"]["tags"] == {"season": "summer"}


@pytest.mark.parametrize("value", [{"nested": "value"}, ["summer"], 3, True])
def test_update_monitoring_site_tags_returns_400_for_non_string_value(client, value):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.patch(
        _detail_url(monitoring_site.id),
        data={"tags": {"season": value}},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_update_monitoring_site_tags_returns_400_for_empty_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.patch(
        _detail_url(monitoring_site.id),
        data={"tags": {"": "summer"}},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_update_monitoring_site_tags_returns_400_for_empty_value(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.patch(
        _detail_url(monitoring_site.id),
        data={"tags": {"season": ""}},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_update_monitoring_site_tags_locks_row_for_update(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as queries:
        client.patch(
            _detail_url(monitoring_site.id),
            data={"tags": {"season": "summer"}},
            content_type="application/json",
        )

    assert any("FOR UPDATE" in query["sql"] for query in queries.captured_queries)


def test_update_monitoring_site_without_tags_does_not_lock_row(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace, name="Original Name")
    client.force_login(owner)

    with CaptureQueriesContext(connection) as queries:
        client.patch(
            _detail_url(monitoring_site.id),
            data={"name": "Updated Name"},
            content_type="application/json",
        )

    assert not any("FOR UPDATE" in query["sql"] for query in queries.captured_queries)


def test_update_monitoring_site_tags_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    monitoring_site.tags = {"season": "summer"}
    monitoring_site.save()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(monitoring_site.id),
        data={"tags": {"season": "winter"}},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_monitoring_site_with_tags_succeeds(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        MONITORING_SITES_URL,
        data=_monitoring_site_body(workspace.id, tags={"season": "summer"}),
        content_type="application/json",
    )

    assert response.status_code == 201
    detail = client.get(_detail_url(response.json()["id"]))
    assert detail.json()["data"]["tags"] == {"season": "summer"}


def test_create_monitoring_site_returns_400_for_null_tag_value(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        MONITORING_SITES_URL,
        data=_monitoring_site_body(workspace.id, tags={"season": None}),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_monitoring_site_returns_400_for_empty_tag_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        MONITORING_SITES_URL,
        data=_monitoring_site_body(workspace.id, tags={"": "summer"}),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_monitoring_site_returns_400_for_empty_tag_value(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        MONITORING_SITES_URL,
        data=_monitoring_site_body(workspace.id, tags={"season": ""}),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- removed tag sub-resource endpoints ---------------------------------------------


@pytest.mark.parametrize("method", ["get", "post", "put", "delete"])
def test_monitoring_site_tags_sub_resource_is_removed(client, method):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = getattr(client, method)(
        _tags_url(monitoring_site.id),
        data={"key": "season", "value": "summer"},
        content_type="application/json",
    )

    assert response.status_code == 404


# --- aggregate read endpoints (basic verification only) ------------------------------


def test_get_monitoring_site_markers_returns_marker_for_public_monitoring_site(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)

    response = client.get(f"{MONITORING_SITES_COLLECTION_URL}/markers")

    assert response.status_code == 200
    assert str(monitoring_site.id) in [m["id"] for m in response.json()]


def test_get_monitoring_site_markers_returns_400_for_malformed_bbox(client):
    response = client.get(f"{MONITORING_SITES_COLLECTION_URL}/markers", {"bbox": "not,a,valid,bbox"})

    assert response.status_code == 400


def test_get_monitoring_site_markers_returns_400_for_out_of_range_bbox(client):
    response = client.get(f"{MONITORING_SITES_COLLECTION_URL}/markers", {"bbox": "-112,40,-111,91"})

    assert response.status_code == 400


def test_get_monitoring_site_markers_filters_public_markers_by_a_bbox_crossing_the_antimeridian(client):
    east = MonitoringSiteFactory(longitude=175, latitude=-15)
    west = MonitoringSiteFactory(longitude=-175, latitude=-15)
    MonitoringSiteFactory(longitude=0, latitude=-15)

    response = client.get(f"{MONITORING_SITES_COLLECTION_URL}/markers", {"bbox": "170,-20,-170,-10"})

    assert response.status_code == 200
    assert {m["id"] for m in response.json()} == {str(east.id), str(west.id)}


def test_get_monitoring_site_markers_filters_private_markers_by_bbox(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    inside = MonitoringSiteFactory(workspace=workspace, private=True, longitude=-111.5, latitude=40.5)
    MonitoringSiteFactory(workspace=workspace, private=True, longitude=-100, latitude=40.5)
    client.force_login(owner)

    response = client.get(f"{MONITORING_SITES_COLLECTION_URL}/markers", {"bbox": "-112,40,-111,41"})

    assert response.status_code == 200
    assert {m["id"] for m in response.json()} == {str(inside.id)}


def test_get_monitoring_site_site_summaries_returns_summary_for_public_monitoring_site(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)

    response = client.get(f"{MONITORING_SITES_COLLECTION_URL}/site-summaries")

    assert response.status_code == 200
    assert str(monitoring_site.id) in [s["id"] for s in response.json()]


def test_get_monitoring_site_task_summaries_returns_summary_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(f"{MONITORING_SITES_COLLECTION_URL}/task-summaries")

    assert response.status_code == 200
    summary = next(s for s in response.json() if s["id"] == str(monitoring_site.id))
    assert summary["productTaskCount"] == 0
    assert summary["monitoringTaskCount"] == 0


def test_get_monitoring_site_tag_keys_returns_keys_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    monitoring_site.tags = {"season": "summer"}
    monitoring_site.save()
    client.force_login(owner)

    response = client.get(f"{MONITORING_SITES_COLLECTION_URL}/tags/keys")

    assert response.status_code == 200
    assert response.json()["season"] == ["summer"]


# --- linked resources ----------------------------------------------------------------


def _linked_resources_url(monitoring_site_id):
    return f"{_detail_url(monitoring_site_id)}/linked-resources"


def _make_monitoring_site_linked_resources(owner, names):
    workspace = WorkspaceFactory(owner=owner)
    parent = MonitoringSiteFactory(workspace=workspace)
    for name in names:
        MonitoringSiteLinkedResource.objects.create(monitoring_site=parent, name=name, type="Report", url=f"https://example.com/{name}")
    return parent


def test_get_monitoring_site_linked_resources_pages_by_name(client):
    owner = UserFactory()
    parent = _make_monitoring_site_linked_resources(owner, ["C", "A", "B"])
    client.force_login(owner)

    first = client.get(_linked_resources_url(parent.id), {"limit": 2}).json()
    second = client.get(_linked_resources_url(parent.id), {"limit": 2, "offset": 2}).json()

    assert [item["name"] for item in first["data"]] == ["A", "B"]
    assert first["meta"] == {"limit": 2, "offset": 0, "totalCount": 3}
    assert "next" in [link["rel"] for link in first["links"]]
    assert [item["name"] for item in second["data"]] == ["C"]


def test_get_monitoring_site_linked_resources_selects_properties(client):
    owner = UserFactory()
    parent = _make_monitoring_site_linked_resources(owner, ["A"])
    client.force_login(owner)

    response = client.get(_linked_resources_url(parent.id), {"properties": "name"})

    assert response.json()["data"] == [{"name": "A"}]


def test_get_monitoring_site_linked_resources_rejects_include(client):
    owner = UserFactory()
    parent = _make_monitoring_site_linked_resources(owner, ["A"])
    client.force_login(owner)

    response = client.get(_linked_resources_url(parent.id), {"include": "monitoringSite"})

    assert response.status_code == 400


def test_get_monitoring_site_linked_resource_returns_item(client):
    owner = UserFactory()
    parent = _make_monitoring_site_linked_resources(owner, ["A", "B"])
    linked_resource = MonitoringSiteLinkedResource.objects.get(monitoring_site=parent, name="B")
    client.force_login(owner)

    response = client.get(f"{_linked_resources_url(parent.id)}/{linked_resource.id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(linked_resource.id)
    assert data["name"] == "B"
    assert data["type"] == "Report"
    assert data["link"] == "https://example.com/B"


def test_get_monitoring_site_linked_resource_returns_404_for_unknown_id(client):
    owner = UserFactory()
    parent = _make_monitoring_site_linked_resources(owner, ["A"])
    client.force_login(owner)

    response = client.get(f"{_linked_resources_url(parent.id)}/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_monitoring_site_linked_resource_returns_404_for_other_parents_resource(client):
    owner = UserFactory()
    parent = _make_monitoring_site_linked_resources(owner, ["A"])
    other_parent = _make_monitoring_site_linked_resources(owner, ["B"])
    other_resource = MonitoringSiteLinkedResource.objects.get(monitoring_site=other_parent)
    client.force_login(owner)

    response = client.get(f"{_linked_resources_url(parent.id)}/{other_resource.id}")

    assert response.status_code == 404


def test_get_monitoring_site_linked_resource_returns_404_for_private_parent_when_outsider(client):
    parent = MonitoringSiteFactory(workspace=WorkspaceFactory(), private=True)
    linked_resource = MonitoringSiteLinkedResource.objects.create(
        monitoring_site=parent, name="A", type="Report", url="https://example.com/A"
    )
    client.force_login(UserFactory())

    response = client.get(f"{_linked_resources_url(parent.id)}/{linked_resource.id}")

    assert response.status_code == 404


def test_add_monitoring_site_linked_resource_succeeds_with_link(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.post(
        _linked_resources_url(monitoring_site.id),
        data={
            "name": "Site Report",
            "type": "Report",
            "link": "https://example.com/report.pdf",
        },
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}
    linked_resources = client.get(_linked_resources_url(monitoring_site.id)).json()["data"]
    assert linked_resources[0]["name"] == "Site Report"


def test_add_monitoring_site_linked_resource_returns_400_for_duplicate_name(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)
    client.post(
        _linked_resources_url(monitoring_site.id),
        data={"name": "Site Report", "type": "Report", "link": "https://example.com/a.pdf"},
    )

    response = client.post(
        _linked_resources_url(monitoring_site.id),
        data={"name": "Site Report", "type": "Report", "link": "https://example.com/b.pdf"},
    )

    assert response.status_code == 400


def test_add_monitoring_site_linked_resource_returns_400_without_file_or_link(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.post(
        _linked_resources_url(monitoring_site.id),
        data={"name": "Site Report", "type": "Report"},
    )

    assert response.status_code == 400


def test_update_monitoring_site_linked_resource_succeeds_for_name(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)
    created = client.post(
        _linked_resources_url(monitoring_site.id),
        data={"name": "Site Report", "type": "Report", "link": "https://example.com/report.pdf"},
    )
    linked_resource_id = created.json()["id"]

    response = client.patch(
        f"{_linked_resources_url(monitoring_site.id)}/{linked_resource_id}",
        data=encode_multipart(BOUNDARY, {"name": "Updated Report"}),
        content_type=MULTIPART_CONTENT,
    )

    assert response.status_code == 204
    assert not response.content
    linked_resources = client.get(_linked_resources_url(monitoring_site.id)).json()["data"]
    assert linked_resources[0]["name"] == "Updated Report"


def test_update_monitoring_site_linked_resource_returns_400_for_mode_switch(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)
    created = client.post(
        _linked_resources_url(monitoring_site.id),
        data={"name": "Site Report", "type": "Report", "link": "https://example.com/report.pdf"},
    )
    linked_resource_id = created.json()["id"]

    response = client.patch(
        f"{_linked_resources_url(monitoring_site.id)}/{linked_resource_id}",
        data=encode_multipart(
            BOUNDARY, {"file": SimpleUploadedFile("photo.png", b"photo")}
        ),
        content_type=MULTIPART_CONTENT,
    )

    assert response.status_code == 400


def test_remove_monitoring_site_linked_resource_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)
    created = client.post(
        _linked_resources_url(monitoring_site.id),
        data={"name": "Site Report", "type": "Report", "link": "https://example.com/report.pdf"},
    )
    linked_resource_id = created.json()["id"]

    response = client.delete(f"{_linked_resources_url(monitoring_site.id)}/{linked_resource_id}")

    assert response.status_code == 204


def test_remove_monitoring_site_linked_resource_returns_404_for_missing_resource(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(
        f"{_linked_resources_url(monitoring_site.id)}/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


# --- include / properties ---------------------------------------------------------


def test_get_monitoring_site_include_sideloads_workspace(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(monitoring_site.id), {"include": "workspace"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(monitoring_site.id)
    assert {row["id"] for row in body["included"]["workspaces"]} == {str(workspace.id)}


def test_get_monitoring_site_include_type_sideloads_monitoring_site_type(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site_type = MonitoringSiteTypeFactory(name="Stream")
    monitoring_site = MonitoringSiteFactory(workspace=workspace, type=monitoring_site_type.name)
    client.force_login(owner)

    response = client.get(_detail_url(monitoring_site.id), {"include": "type"})

    assert response.status_code == 200
    included = response.json()["included"]
    assert {row["id"] for row in included["monitoringSiteTypes"]} == {
        str(monitoring_site_type.id)
    }


def test_get_monitoring_site_without_include_omits_included_bucket(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(monitoring_site.id))

    assert response.status_code == 200
    assert not response.json().get("included")


def test_get_monitoring_sites_include_does_not_scale_queries_with_site_count(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    for _ in range(5):
        MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(MONITORING_SITES_URL, {"include": "workspace"})

    for _ in range(5):
        MonitoringSiteFactory(workspace=workspace)

    with CaptureQueriesContext(connection) as large:
        client.get(MONITORING_SITES_URL, {"include": "workspace"})

    assert len(large.captured_queries) == len(small.captured_queries)


def test_get_monitoring_sites_properties_filters_response_fields(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(MONITORING_SITES_URL, {"properties": "id,name"})

    assert response.status_code == 200
    row = response.json()["data"][0]
    assert set(row.keys()) == {"id", "name"}
