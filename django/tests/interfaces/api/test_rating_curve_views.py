import pytest

from django.test.utils import CaptureQueriesContext
from django.db import connection

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import MonitoringSiteFactory
from tests.processing.products.factories import RatingCurveFactory, RatingCurvePointFactory

pytestmark = pytest.mark.django_db

RATING_CURVES_URL = "/api/data/data-product-rating-curves"

RATING_CURVE_FIELDS = {
    "id",
    "name",
    "description",
    "fittingMethod",
    "monitoringSiteId",
    "points",
}


def _detail_url(rating_curve_id):
    return f"{RATING_CURVES_URL}/{rating_curve_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="RatingCurve", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_rating_curve(workspace, **kwargs):
    return RatingCurveFactory(monitoring_site=MonitoringSiteFactory(workspace=workspace), **kwargs)


def _rating_curve_body(monitoring_site_id, **overrides):
    body = {
        "name": "New Rating Curve",
        "fittingMethod": "linear",
        "monitoringSiteId": str(monitoring_site_id),
        "points": [[1.0, 2.0], [3.0, 4.0]],
    }
    body.update(overrides)
    return body


# --- get_rating_curves ---------------------------------------------------------------


def test_get_rating_curves_includes_curve_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    rating_curve = _make_rating_curve(workspace)
    client.force_login(owner)

    response = client.get(RATING_CURVES_URL)

    assert response.status_code == 200
    assert str(rating_curve.id) in [r["id"] for r in response.json()["data"]]


def test_get_rating_curves_excludes_curve_for_outsider(client):
    workspace = WorkspaceFactory()
    _make_rating_curve(workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(RATING_CURVES_URL)

    assert response.json()["data"] == []


def test_get_rating_curves_returns_401_when_unauthenticated(client):
    response = client.get(RATING_CURVES_URL)

    assert response.status_code == 401


def test_get_rating_curves_points_survive_the_response_wrappers_double_validation(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    curve_a = _make_rating_curve(workspace, name="Curve A")
    curve_b = _make_rating_curve(workspace, name="Curve B")
    RatingCurvePointFactory(rating_curve=curve_a, input_value=1.0, output_value=2.0)
    RatingCurvePointFactory(rating_curve=curve_a, input_value=3.0, output_value=4.0)
    RatingCurvePointFactory(rating_curve=curve_b, input_value=5.0, output_value=6.0)
    client.force_login(owner)

    response = client.get(RATING_CURVES_URL)

    assert response.status_code == 200
    by_id = {r["id"]: r for r in response.json()["data"]}
    assert by_id[str(curve_a.id)]["points"] == [[1.0, 2.0], [3.0, 4.0]]
    assert by_id[str(curve_b.id)]["points"] == [[5.0, 6.0]]


def test_get_rating_curves_properties_filters_every_item_in_the_list(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    _make_rating_curve(workspace, name="Curve A")
    _make_rating_curve(workspace, name="Curve B")
    client.force_login(owner)

    response = client.get(RATING_CURVES_URL, {"properties": "id,name"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "name"}


def test_get_rating_curves_properties_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    _make_rating_curve(workspace)
    client.force_login(owner)

    response = client.get(RATING_CURVES_URL, {"properties": ["id", "name"]})

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name"}


def test_get_rating_curves_properties_rejects_unknown_property(client):
    client.force_login(UserFactory())

    response = client.get(RATING_CURVES_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_rating_curves_without_properties_returns_every_field(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    _make_rating_curve(workspace)
    client.force_login(owner)

    response = client.get(RATING_CURVES_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == RATING_CURVE_FIELDS


def test_get_rating_curves_has_no_included_key_without_include_param(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    _make_rating_curve(workspace)
    client.force_login(owner)

    response = client.get(RATING_CURVES_URL)

    assert response.status_code == 200
    assert "included" not in response.json()


def test_get_rating_curves_include_monitoring_site_deduplicates_across_items(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    RatingCurveFactory(monitoring_site=monitoring_site)
    RatingCurveFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.get(RATING_CURVES_URL, {"include": "monitoringSite"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert [s["id"] for s in body["included"]["monitoringSites"]] == [str(monitoring_site.id)]


def test_get_rating_curves_include_rejects_unknown_relation(client):
    client.force_login(UserFactory())

    response = client.get(RATING_CURVES_URL, {"include": "bogus"})

    assert response.status_code == 400


def test_get_rating_curves_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    RatingCurveFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.get(RATING_CURVES_URL, {"include": ["monitoringSite"]})

    assert response.status_code == 200
    body = response.json()
    assert [s["id"] for s in body["included"]["monitoringSites"]] == [str(monitoring_site.id)]


def test_get_rating_curves_properties_and_include_together(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    RatingCurveFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.get(
        RATING_CURVES_URL, {"properties": "id,name", "include": "monitoringSite"}
    )

    assert response.status_code == 200
    body = response.json()
    for item in body["data"]:
        assert set(item.keys()) == {"id", "name"}
    assert body["included"]["monitoringSites"][0]["id"] == str(monitoring_site.id)


def test_get_rating_curves_properties_does_not_filter_included_resources(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace, name="Acme Site")
    RatingCurveFactory(monitoring_site=monitoring_site, name="Curve A")
    client.force_login(owner)

    response = client.get(
        RATING_CURVES_URL, {"properties": "name", "include": "monitoringSite"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"][0] == {"name": "Curve A"}
    included_site = body["included"]["monitoringSites"][0]
    assert included_site["id"] == str(monitoring_site.id)
    assert included_site["name"] == "Acme Site"


def test_get_rating_curves_include_monitoring_site_does_not_scale_queries_with_curve_count(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    for _ in range(5):
        RatingCurveFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(RATING_CURVES_URL, {"include": "monitoringSite"})

    for _ in range(5):
        RatingCurveFactory(monitoring_site=monitoring_site)

    with CaptureQueriesContext(connection) as large:
        client.get(RATING_CURVES_URL, {"include": "monitoringSite"})

    assert len(large.captured_queries) == len(small.captured_queries)


def test_get_rating_curves_filters_by_monitoring_site_id(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    site_a = MonitoringSiteFactory(workspace=workspace)
    site_b = MonitoringSiteFactory(workspace=workspace)
    curve_a = RatingCurveFactory(monitoring_site=site_a)
    RatingCurveFactory(monitoring_site=site_b)
    client.force_login(owner)

    response = client.get(RATING_CURVES_URL, {"monitoring_site_id": str(site_a.id)})

    assert response.status_code == 200
    assert [r["id"] for r in response.json()["data"]] == [str(curve_a.id)]


def test_get_rating_curves_filters_by_workspace_id(client):
    owner = UserFactory()
    workspace_a = WorkspaceFactory(owner=owner)
    workspace_b = WorkspaceFactory(owner=owner)
    curve_a = _make_rating_curve(workspace_a)
    _make_rating_curve(workspace_b)
    client.force_login(owner)

    response = client.get(RATING_CURVES_URL, {"workspace_id": str(workspace_a.id)})

    assert response.status_code == 200
    assert [r["id"] for r in response.json()["data"]] == [str(curve_a.id)]


@pytest.mark.parametrize(
    "sortby_value,expected_order",
    [
        ("name", ["A Curve", "B Curve"]),
        ("-name", ["B Curve", "A Curve"]),
        ("monitoringSiteName", ["A Curve", "B Curve"]),
        ("workspaceName", ["A Curve", "B Curve"]),
    ],
)
def test_get_rating_curves_sorts_by_requested_field(client, sortby_value, expected_order):
    owner = UserFactory()
    workspace_a = WorkspaceFactory(owner=owner, name="Workspace A")
    workspace_b = WorkspaceFactory(owner=owner, name="Workspace B")
    site_a = MonitoringSiteFactory(workspace=workspace_a, name="Site A")
    site_b = MonitoringSiteFactory(workspace=workspace_b, name="Site B")
    RatingCurveFactory(monitoring_site=site_a, name="A Curve")
    RatingCurveFactory(monitoring_site=site_b, name="B Curve")
    client.force_login(owner)

    response = client.get(RATING_CURVES_URL, {"sortby": sortby_value})

    assert response.status_code == 200
    assert [r["name"] for r in response.json()["data"]] == expected_order


def test_get_rating_curves_sorts_by_workspace_id(client):
    owner = UserFactory()
    workspace_a = WorkspaceFactory(owner=owner)
    workspace_b = WorkspaceFactory(owner=owner)
    site_a = MonitoringSiteFactory(workspace=workspace_a)
    site_b = MonitoringSiteFactory(workspace=workspace_b)
    RatingCurveFactory(monitoring_site=site_a, name="First")
    RatingCurveFactory(monitoring_site=site_b, name="Second")
    client.force_login(owner)

    response = client.get(RATING_CURVES_URL, {"sortby": "workspaceId"})

    workspace_ids_sorted = sorted([str(workspace_a.id), str(workspace_b.id)])
    expected_first_name = "First" if workspace_ids_sorted[0] == str(workspace_a.id) else "Second"

    assert response.status_code == 200
    assert response.json()["data"][0]["name"] == expected_first_name


def test_get_rating_curves_sortby_rejects_unknown_field(client):
    client.force_login(UserFactory())

    response = client.get(RATING_CURVES_URL, {"sortby": "bogus"})

    assert response.status_code == 400


# --- create_rating_curve ---------------------------------------------------------------


def test_create_rating_curve_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.post(
        RATING_CURVES_URL,
        data=_rating_curve_body(monitoring_site.id),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}

    detail = client.get(_detail_url(response.json()["id"]))
    body = detail.json()["data"]
    assert body["name"] == "New Rating Curve"
    assert body["points"] == [[1.0, 2.0], [3.0, 4.0]]


def test_create_rating_curve_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)

    response = client.post(
        RATING_CURVES_URL,
        data=_rating_curve_body(monitoring_site.id),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_rating_curve_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        RATING_CURVES_URL,
        data=_rating_curve_body(monitoring_site.id),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_rating_curve_returns_409_for_duplicate_input_value_in_points(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.post(
        RATING_CURVES_URL,
        data=_rating_curve_body(monitoring_site.id, points=[[1.0, 2.0], [1.0, 5.0]]),
        content_type="application/json",
    )

    assert response.status_code == 409


# --- get_rating_curve ----------------------------------------------------------------------


def test_get_rating_curve_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    rating_curve = _make_rating_curve(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(rating_curve.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(rating_curve.id)


def test_get_rating_curve_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    rating_curve = _make_rating_curve(workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(rating_curve.id))

    assert response.status_code == 404


def test_get_rating_curve_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    rating_curve = _make_rating_curve(workspace)

    response = client.get(_detail_url(rating_curve.id))

    assert response.status_code == 401


def test_get_rating_curve_returns_404_for_nonexistent_curve(client):
    owner = UserFactory()
    client.force_login(owner)

    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_rating_curve_properties_rejects_unknown_property(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    rating_curve = _make_rating_curve(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(rating_curve.id), {"properties": "bogus"})

    assert response.status_code == 400


def test_get_rating_curve_included_is_present_but_empty_without_include_param(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    rating_curve = _make_rating_curve(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(rating_curve.id))

    assert response.status_code == 200
    body = response.json()
    assert "included" in body
    assert body["included"] == {}


def test_get_rating_curve_include_monitoring_site_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.get(_detail_url(rating_curve.id), {"include": "monitoringSite"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(rating_curve.id)
    assert [s["id"] for s in body["included"]["monitoringSites"]] == [str(monitoring_site.id)]


def test_get_rating_curve_include_rejects_unknown_relation(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    rating_curve = _make_rating_curve(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(rating_curve.id), {"include": "bogus"})

    assert response.status_code == 400


def test_get_rating_curve_include_accepts_repeated_key_style_too(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.get(_detail_url(rating_curve.id), {"include": ["monitoringSite"]})

    assert response.status_code == 200
    body = response.json()
    assert [s["id"] for s in body["included"]["monitoringSites"]] == [str(monitoring_site.id)]


# --- update_rating_curve ----------------------------------------------------------------------


def test_update_rating_curve_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    rating_curve = _make_rating_curve(workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(rating_curve.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(rating_curve.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_rating_curve_replaces_points(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    rating_curve = _make_rating_curve(workspace)
    RatingCurvePointFactory(rating_curve=rating_curve, input_value=1.0, output_value=2.0)
    client.force_login(owner)

    response = client.patch(
        _detail_url(rating_curve.id),
        data={"points": [[9.0, 8.0]]},
        content_type="application/json",
    )

    assert response.status_code == 204

    detail = client.get(_detail_url(rating_curve.id))
    assert detail.json()["data"]["points"] == [[9.0, 8.0]]


def test_update_rating_curve_rolls_back_points_on_duplicate_input_value(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    rating_curve = _make_rating_curve(workspace)
    RatingCurvePointFactory(rating_curve=rating_curve, input_value=1.0, output_value=2.0)
    client.force_login(owner)

    response = client.patch(
        _detail_url(rating_curve.id),
        data={"points": [[9.0, 8.0], [9.0, 7.0]]},
        content_type="application/json",
    )

    assert response.status_code == 409

    detail = client.get(_detail_url(rating_curve.id))
    assert detail.json()["data"]["points"] == [[1.0, 2.0]]


def test_update_rating_curve_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    rating_curve = _make_rating_curve(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(rating_curve.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_rating_curve ----------------------------------------------------------------------


def test_delete_rating_curve_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    rating_curve = _make_rating_curve(workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(rating_curve.id))

    assert response.status_code == 204
    assert client.get(_detail_url(rating_curve.id)).status_code == 404


def test_delete_rating_curve_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    rating_curve = _make_rating_curve(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(rating_curve.id))

    assert response.status_code == 403
