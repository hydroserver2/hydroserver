import pytest

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import LocationFactory, ThingFactory
from tests.processing.products.factories import RatingCurveFactory

pytestmark = pytest.mark.django_db

RATING_CURVES_URL = "/api/data/products/rating-curves"


def _detail_url(rating_curve_id):
    return f"{RATING_CURVES_URL}/{rating_curve_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="RatingCurve", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_thing_with_location(workspace, **kwargs):
    thing = ThingFactory(workspace=workspace, **kwargs)
    LocationFactory(thing=thing, latitude=40.0, longitude=-111.0)
    return thing


def _make_rating_curve(workspace, **kwargs):
    return RatingCurveFactory(thing=_make_thing_with_location(workspace), **kwargs)


def _rating_curve_body(thing_id, **overrides):
    body = {
        "name": "New Rating Curve",
        "fittingMethod": "linear",
        "thingId": str(thing_id),
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
    assert str(rating_curve.id) in [r["id"] for r in response.json()]


def test_get_rating_curves_excludes_curve_for_outsider(client):
    workspace = WorkspaceFactory()
    _make_rating_curve(workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(RATING_CURVES_URL)

    assert response.json() == []


def test_get_rating_curves_returns_401_when_unauthenticated(client):
    response = client.get(RATING_CURVES_URL)

    assert response.status_code == 401


# --- create_rating_curve ---------------------------------------------------------------


def test_create_rating_curve_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = _make_thing_with_location(workspace)
    client.force_login(owner)

    response = client.post(
        RATING_CURVES_URL,
        data=_rating_curve_body(thing.id),
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "New Rating Curve"
    assert body["points"] == [[1.0, 2.0], [3.0, 4.0]]


def test_create_rating_curve_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    thing = _make_thing_with_location(workspace)

    response = client.post(
        RATING_CURVES_URL,
        data=_rating_curve_body(thing.id),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_rating_curve_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    thing = _make_thing_with_location(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        RATING_CURVES_URL,
        data=_rating_curve_body(thing.id),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_rating_curve_returns_400_for_duplicate_input_value_in_points(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = _make_thing_with_location(workspace)
    client.force_login(owner)

    response = client.post(
        RATING_CURVES_URL,
        data=_rating_curve_body(thing.id, points=[[1.0, 2.0], [1.0, 5.0]]),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_rating_curve ----------------------------------------------------------------------


def test_get_rating_curve_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    rating_curve = _make_rating_curve(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(rating_curve.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(rating_curve.id)


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

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


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
