import uuid
import pytest
from collections import Counter
from ninja.errors import HttpError
from processing.products.services.rating_curve import RatingCurveService
from processing.products.models import RatingCurve

rating_curve_service = RatingCurveService()

RC1 = "019c0002-0000-7000-8000-000000000001"  # private workspace, private thing
RC2 = "019c0002-0000-7000-8000-000000000002"  # public workspace, public thing
PRIVATE_THING = "76dadda5-224b-4e1f-8570-e385bd482b2d"
PUBLIC_THING = "3b7818af-eff7-4149-8517-e5cad9dc22e1"
PRIVATE_WORKSPACE = "b27c51a0-7374-462d-8a53-d97d47176c10"
PUBLIC_WORKSPACE = "6e0deaf2-a92b-421b-9ece-86783265596f"
NONEXISTENT = "00000000-0000-0000-0000-000000000000"


def _err(exc_info):
    val = exc_info.value
    return val.message if isinstance(val, HttpError) else str(val)


@pytest.mark.parametrize(
    "principal, params, expected_names, max_queries",
    [
        # User access — both workspaces visible
        ("owner", {}, ["Test Rating Curve", "Test Public Rating Curve"], 10),
        ("editor", {}, ["Test Rating Curve", "Test Public Rating Curve"], 10),
        ("viewer", {}, ["Test Rating Curve", "Test Public Rating Curve"], 10),
        ("admin", {}, ["Test Rating Curve", "Test Public Rating Curve"], 10),
        # API key has view access to public workspace only
        ("apikey", {}, ["Test Public Rating Curve"], 10),
        # No access
        ("unaffiliated", {}, [], 10),
        ("anonymous", {}, [], 10),
        # Pagination
        ("owner", {"page": 2, "page_size": 1}, ["Test Rating Curve"], 10),
        # Thing filter
        ("owner", {"thing": [uuid.UUID(PRIVATE_THING)]}, ["Test Rating Curve"], 10),
        ("owner", {"thing": [uuid.UUID(PUBLIC_THING)]}, ["Test Public Rating Curve"], 10),
        # Workspace filter
        ("owner", {"workspace": [uuid.UUID(PRIVATE_WORKSPACE)]}, ["Test Rating Curve"], 10),
        ("owner", {"workspace": [uuid.UUID(PUBLIC_WORKSPACE)]}, ["Test Public Rating Curve"], 10),
    ],
)
def test_list_rating_curves(
    django_assert_max_num_queries, get_principal, principal, params, expected_names, max_queries
):
    with django_assert_max_num_queries(max_queries):
        count, curves = rating_curve_service.get_collection(
            principal=get_principal(principal),
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=params.pop("order_by", []),
            **params,
        )
        assert Counter(c.name for c in curves) == Counter(expected_names)


@pytest.mark.parametrize(
    "principal, rating_curve, expected_name, error, error_fragment",
    [
        # Successful reads
        ("owner", RC1, "Test Rating Curve", None, None),
        ("owner", RC2, "Test Public Rating Curve", None, None),
        ("editor", RC1, "Test Rating Curve", None, None),
        ("viewer", RC1, "Test Rating Curve", None, None),
        ("admin", RC1, "Test Rating Curve", None, None),
        # API key can view public workspace rating curves
        ("apikey", RC2, "Test Public Rating Curve", None, None),
        # API key cannot see private workspace rating curves
        ("apikey", RC1, None, LookupError, "does not exist"),
        # No access
        ("unaffiliated", RC1, None, LookupError, "does not exist"),
        ("anonymous", RC1, None, LookupError, "does not exist"),
        # Not found
        ("owner", NONEXISTENT, None, LookupError, "does not exist"),
    ],
)
def test_get_rating_curve(get_principal, principal, rating_curve, expected_name, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            rating_curve_service.get(
                rating_curve=uuid.UUID(rating_curve),
                principal=get_principal(principal),
            )
        assert error_fragment in _err(exc_info)
    else:
        result = rating_curve_service.get(
            rating_curve=uuid.UUID(rating_curve),
            principal=get_principal(principal),
        )
        assert result.name == expected_name


def test_get_rating_curve_includes_points(get_principal):
    result = rating_curve_service.get(
        rating_curve=uuid.UUID(RC1),
        principal=get_principal("owner"),
    )
    points = list(result.points.all())
    assert len(points) == 2
    assert points[0].input_value == 1.0
    assert points[0].output_value == 2.0
    assert points[1].input_value == 2.0
    assert points[1].output_value == 4.0


@pytest.mark.parametrize(
    "principal, thing, error, error_fragment",
    [
        ("owner", PRIVATE_THING, None, None),
        ("owner", PUBLIC_THING, None, None),
        ("editor", PRIVATE_THING, None, None),
        ("admin", PRIVATE_THING, None, None),
        # Viewer has no create permission
        ("viewer", PRIVATE_THING, PermissionError, "do not have permission"),
        ("viewer", PUBLIC_THING, PermissionError, "do not have permission"),
        # API key has view-only access
        ("apikey", PUBLIC_THING, PermissionError, "do not have permission"),
        # Unaffiliated: thing is found but create is denied
        ("unaffiliated", PRIVATE_THING, PermissionError, "do not have permission"),
        ("unaffiliated", PUBLIC_THING, PermissionError, "do not have permission"),
        # Not found
        ("owner", NONEXISTENT, HttpError, "does not exist"),
    ],
)
def test_create_rating_curve(get_principal, principal, thing, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            rating_curve_service.create(
                principal=get_principal(principal),
                thing=uuid.UUID(thing),
                name="New Rating Curve",
                fitting_method="linear",
            )
        assert error_fragment in _err(exc_info)
    else:
        result = rating_curve_service.create(
            principal=get_principal(principal),
            thing=uuid.UUID(thing),
            name="New Rating Curve",
            fitting_method="linear",
        )
        assert result.name == "New Rating Curve"
        assert result.fitting_method == "linear"
        assert result.thing_id == uuid.UUID(thing)


def test_create_rating_curve_with_points(get_principal):
    result = rating_curve_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_THING),
        name="Curve with Points",
        fitting_method="power_law",
        points=[(0.5, 1.0), (1.0, 2.5), (2.0, None)],
    )
    points = list(result.points.all())
    assert len(points) == 3
    assert points[0].input_value == 0.5
    assert points[0].output_value == 1.0
    assert points[2].output_value is None


def test_create_rating_curve_duplicate_points_rejected(get_principal):
    with pytest.raises(ValueError) as exc_info:
        rating_curve_service.create(
            principal=get_principal("owner"),
            thing=uuid.UUID(PRIVATE_THING),
            name="Bad Curve",
            fitting_method="linear",
            points=[(1.0, 2.0), (1.0, 3.0)],
        )
    assert "Duplicate" in str(exc_info.value)


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        # View-only
        ("viewer", PermissionError, "do not have permission"),
        # Not visible
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_update_rating_curve(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            rating_curve_service.update(
                rating_curve=uuid.UUID(RC1),
                principal=get_principal(principal),
                name="Updated Rating Curve",
            )
        assert error_fragment in _err(exc_info)
    else:
        result = rating_curve_service.update(
            rating_curve=uuid.UUID(RC1),
            principal=get_principal(principal),
            name="Updated Rating Curve",
        )
        assert result.name == "Updated Rating Curve"


def test_update_rating_curve_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        rating_curve_service.update(
            rating_curve=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
            name="Updated",
        )
    assert "does not exist" in str(exc_info.value)


def test_update_rating_curve_replaces_points(get_principal):
    result = rating_curve_service.update(
        rating_curve=uuid.UUID(RC1),
        principal=get_principal("owner"),
        points=[(5.0, 10.0), (10.0, 20.0), (15.0, 30.0)],
    )
    points = list(result.points.all())
    assert len(points) == 3
    assert points[0].input_value == 5.0


def test_update_rating_curve_clears_points(get_principal):
    result = rating_curve_service.update(
        rating_curve=uuid.UUID(RC1),
        principal=get_principal("owner"),
        points=[],
    )
    assert result.points.count() == 0


def test_update_rating_curve_changes_fitting_method(get_principal):
    result = rating_curve_service.update(
        rating_curve=uuid.UUID(RC1),
        principal=get_principal("owner"),
        fitting_method="spline",
    )
    assert result.fitting_method == "spline"


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        # View-only
        ("viewer", PermissionError, "do not have permission"),
        # Not visible
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_delete_rating_curve(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            rating_curve_service.delete(
                rating_curve=uuid.UUID(RC1),
                principal=get_principal(principal),
            )
        assert error_fragment in _err(exc_info)
    else:
        rating_curve_service.delete(
            rating_curve=uuid.UUID(RC1),
            principal=get_principal(principal),
        )
        assert not RatingCurve.objects.filter(pk=uuid.UUID(RC1)).exists()


def test_delete_rating_curve_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        rating_curve_service.delete(
            rating_curve=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)