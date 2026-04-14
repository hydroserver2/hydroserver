import uuid
import pytest
import numpy as np
from collections import Counter
from ninja.errors import HttpError
from processing.products.services.rating_curve import RatingCurveService
from processing.products.models import RatingCurve

rating_curve_service = RatingCurveService()

RC1 = "019c0002-0000-7000-8000-000000000001"  # private workspace, private thing (referenced by T_RC — PROTECTED)
RC2 = "019c0002-0000-7000-8000-000000000002"  # public workspace, public thing
RC3 = "019c0002-0000-7000-8000-000000000003"  # private workspace, no transformations (safe to delete)
PRIVATE_THING = "76dadda5-224b-4e1f-8570-e385bd482b2d"
PUBLIC_THING = "3b7818af-eff7-4149-8517-e5cad9dc22e1"
PRIVATE_WORKSPACE = "b27c51a0-7374-462d-8a53-d97d47176c10"
PUBLIC_WORKSPACE = "6e0deaf2-a92b-421b-9ece-86783265596f"
NONEXISTENT = "00000000-0000-0000-0000-000000000000"


def _err(exc_info):
    val = exc_info.value
    return val.message if isinstance(val, HttpError) else str(val)


PRIVATE_RC_NAMES = ["Test Rating Curve", "Test Disposable Rating Curve"]
ALL_RC_NAMES = PRIVATE_RC_NAMES + ["Test Public Rating Curve"]


@pytest.mark.parametrize(
    "principal, params, expected_names, max_queries",
    [
        # User access — all 3 rating curves visible (2 private, 1 public)
        ("owner", {}, ALL_RC_NAMES, 10),
        ("editor", {}, ALL_RC_NAMES, 10),
        ("viewer", {}, ALL_RC_NAMES, 10),
        ("admin", {}, ALL_RC_NAMES, 10),
        # API key has view access to public workspace only
        ("apikey", {}, ["Test Public Rating Curve"], 10),
        # No access
        ("unaffiliated", {}, [], 10),
        ("anonymous", {}, [], 10),
        # Pagination — ordered by -id; RC3 newest, then RC2, then RC1; page 3 = RC1
        ("owner", {"page": 3, "page_size": 1}, ["Test Rating Curve"], 10),
        # Thing filter
        ("owner", {"thing": [uuid.UUID(PRIVATE_THING)]}, PRIVATE_RC_NAMES, 10),
        ("owner", {"thing": [uuid.UUID(PUBLIC_THING)]}, ["Test Public Rating Curve"], 10),
        # Workspace filter
        ("owner", {"workspace": [uuid.UUID(PRIVATE_WORKSPACE)]}, PRIVATE_RC_NAMES, 10),
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
        ("owner", NONEXISTENT, LookupError, "does not exist"),
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
        points=[(0.5, 1.0), (1.0, 2.5), (2.0, 5.0)],
    )
    points = list(result.points.all())
    assert len(points) == 3
    assert points[0].input_value == 0.5
    assert points[0].output_value == 1.0
    assert points[2].output_value == 5.0


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
                rating_curve=uuid.UUID(RC3),
                principal=get_principal(principal),
            )
        assert error_fragment in _err(exc_info)
    else:
        rating_curve_service.delete(
            rating_curve=uuid.UUID(RC3),
            principal=get_principal(principal),
        )
        assert not RatingCurve.objects.filter(pk=uuid.UUID(RC3)).exists()


def test_delete_rating_curve_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        rating_curve_service.delete(
            rating_curve=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)


# --- apply_rating_curve ---

def test_apply_rating_curve_linear_within_range():
    """RC1 is linear with points (1→2, 2→4). y = 2x."""
    result = rating_curve_service.apply_rating_curve(
        rating_curve=uuid.UUID(RC1),
        input_values=np.array([1.0, 1.5, 2.0]),
    )
    np.testing.assert_allclose(result, [2.0, 3.0, 4.0])


def test_apply_rating_curve_linear_outside_range_gives_nan():
    """Values outside the control point range should be NaN for linear method."""
    result = rating_curve_service.apply_rating_curve(
        rating_curve=uuid.UUID(RC1),
        input_values=np.array([0.0, 3.0]),
    )
    assert np.isnan(result[0])
    assert np.isnan(result[1])


def test_apply_rating_curve_too_few_points_returns_all_nan():
    """RC2 has no points; result should be all NaN."""
    result = rating_curve_service.apply_rating_curve(
        rating_curve=uuid.UUID(RC2),
        input_values=np.array([1.0, 2.0]),
    )
    assert np.all(np.isnan(result))


def test_apply_rating_curve_power_law(get_principal):
    """Create a power_law curve with known coefficients and verify interpolation."""
    # Points that exactly fit y = 2 * x^2: (1, 2), (2, 8), (4, 32)
    rc = rating_curve_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_THING),
        name="Power Law Curve",
        fitting_method="power_law",
        points=[(1.0, 2.0), (2.0, 8.0), (4.0, 32.0)],
    )
    result = rating_curve_service.apply_rating_curve(
        rating_curve=rc.pk,
        input_values=np.array([1.0, 2.0, 4.0]),
    )
    np.testing.assert_allclose(result, [2.0, 8.0, 32.0], rtol=1e-4)


def test_apply_rating_curve_power_law_non_positive_input_gives_nan(get_principal):
    """Power law is undefined for x ≤ 0; those values should be NaN."""
    rc = rating_curve_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_THING),
        name="Power Law NaN Curve",
        fitting_method="power_law",
        points=[(1.0, 2.0), (2.0, 8.0)],
    )
    result = rating_curve_service.apply_rating_curve(
        rating_curve=rc.pk,
        input_values=np.array([-1.0, 0.0, 1.0]),
    )
    assert np.isnan(result[0])
    assert np.isnan(result[1])
    assert not np.isnan(result[2])


def test_apply_rating_curve_polynomial(get_principal):
    """Create a polynomial curve and check it passes through control points."""
    rc = rating_curve_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_THING),
        name="Polynomial Curve",
        fitting_method="polynomial",
        points=[(0.0, 0.0), (1.0, 1.0), (2.0, 4.0), (3.0, 9.0)],
    )
    result = rating_curve_service.apply_rating_curve(
        rating_curve=rc.pk,
        input_values=np.array([0.0, 1.0, 2.0, 3.0]),
    )
    np.testing.assert_allclose(result, [0.0, 1.0, 4.0, 9.0], atol=1e-6)
