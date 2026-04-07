import uuid
import pytest
from collections import Counter
from ninja.errors import HttpError
from processing.products.services.expression import ExpressionService
from processing.products.models import Expression

expression_service = ExpressionService()

EXP1 = "019c0001-0000-7000-8000-000000000001"  # private workspace, private thing
EXP2 = "019c0001-0000-7000-8000-000000000002"  # public workspace, public thing
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
        # User access — both workspaces visible to owner/editor/viewer/admin
        ("owner", {}, ["Test Expression", "Test Public Expression"], 10),
        ("editor", {}, ["Test Expression", "Test Public Expression"], 10),
        ("viewer", {}, ["Test Expression", "Test Public Expression"], 10),
        ("admin", {}, ["Test Expression", "Test Public Expression"], 10),
        # API key has view access to public workspace only
        ("apikey", {}, ["Test Public Expression"], 10),
        # No access
        ("unaffiliated", {}, [], 10),
        ("anonymous", {}, [], 10),
        # Pagination — page 2 with page_size=1 returns the alphabetically lower name (desc order by id)
        ("owner", {"page": 2, "page_size": 1}, ["Test Expression"], 10),
        # Thing filter
        ("owner", {"thing": [uuid.UUID(PRIVATE_THING)]}, ["Test Expression"], 10),
        ("owner", {"thing": [uuid.UUID(PUBLIC_THING)]}, ["Test Public Expression"], 10),
        # Workspace filter
        ("owner", {"workspace": [uuid.UUID(PRIVATE_WORKSPACE)]}, ["Test Expression"], 10),
        ("owner", {"workspace": [uuid.UUID(PUBLIC_WORKSPACE)]}, ["Test Public Expression"], 10),
    ],
)
def test_list_expressions(
    django_assert_max_num_queries, get_principal, principal, params, expected_names, max_queries
):
    with django_assert_max_num_queries(max_queries):
        count, expressions = expression_service.get_collection(
            principal=get_principal(principal),
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=params.pop("order_by", []),
            **params,
        )
        assert Counter(e.name for e in expressions) == Counter(expected_names)


@pytest.mark.parametrize(
    "principal, expression, expected_name, error, error_fragment",
    [
        # Successful reads
        ("owner", EXP1, "Test Expression", None, None),
        ("owner", EXP2, "Test Public Expression", None, None),
        ("editor", EXP1, "Test Expression", None, None),
        ("viewer", EXP1, "Test Expression", None, None),
        ("admin", EXP1, "Test Expression", None, None),
        # API key can view public workspace expressions
        ("apikey", EXP2, "Test Public Expression", None, None),
        # API key cannot see private workspace expressions
        ("apikey", EXP1, None, LookupError, "does not exist"),
        # No access
        ("unaffiliated", EXP1, None, LookupError, "does not exist"),
        ("anonymous", EXP1, None, LookupError, "does not exist"),
        # Not found
        ("owner", NONEXISTENT, None, LookupError, "does not exist"),
    ],
)
def test_get_expression(get_principal, principal, expression, expected_name, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            expression_service.get(
                expression=uuid.UUID(expression),
                principal=get_principal(principal),
            )
        assert error_fragment in _err(exc_info)
    else:
        result = expression_service.get(
            expression=uuid.UUID(expression),
            principal=get_principal(principal),
        )
        assert result.name == expected_name


def test_get_expression_includes_formula(get_principal):
    result = expression_service.get(
        expression=uuid.UUID(EXP1),
        principal=get_principal("owner"),
    )
    assert result.formula == "x + y"


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
        # Unaffiliated: thing is found (no visibility filter) but create is denied
        ("unaffiliated", PRIVATE_THING, PermissionError, "do not have permission"),
        ("unaffiliated", PUBLIC_THING, PermissionError, "do not have permission"),
        # Not found
        ("owner", NONEXISTENT, HttpError, "does not exist"),
    ],
)
def test_create_expression(get_principal, principal, thing, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            expression_service.create(
                principal=get_principal(principal),
                thing=uuid.UUID(thing),
                name="New Expression",
            )
        assert error_fragment in _err(exc_info)
    else:
        result = expression_service.create(
            principal=get_principal(principal),
            thing=uuid.UUID(thing),
            name="New Expression",
        )
        assert result.name == "New Expression"
        assert result.thing_id == uuid.UUID(thing)


def test_create_expression_with_formula(get_principal):
    result = expression_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_THING),
        name="Formula Expression",
        formula="a * b + c",
    )
    assert result.formula == "a * b + c"


def test_create_expression_invalid_formula(get_principal):
    with pytest.raises(ValueError) as exc_info:
        expression_service.create(
            principal=get_principal("owner"),
            thing=uuid.UUID(PRIVATE_THING),
            name="Bad Expression",
            formula="import os",
        )
    assert "unsupported" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


def test_create_expression_syntax_error(get_principal):
    with pytest.raises(ValueError) as exc_info:
        expression_service.create(
            principal=get_principal("owner"),
            thing=uuid.UUID(PRIVATE_THING),
            name="Syntax Error Expression",
            formula="x +* y",
        )
    assert "invalid" in str(exc_info.value).lower()


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
def test_update_expression(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            expression_service.update(
                expression=uuid.UUID(EXP1),
                principal=get_principal(principal),
                name="Updated Expression",
            )
        assert error_fragment in _err(exc_info)
    else:
        result = expression_service.update(
            expression=uuid.UUID(EXP1),
            principal=get_principal(principal),
            name="Updated Expression",
        )
        assert result.name == "Updated Expression"


def test_update_expression_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        expression_service.update(
            expression=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
            name="Updated",
        )
    assert "does not exist" in str(exc_info.value)


def test_update_expression_formula(get_principal):
    result = expression_service.update(
        expression=uuid.UUID(EXP1),
        principal=get_principal("owner"),
        formula="a - b",
    )
    assert result.formula == "a - b"


def test_update_expression_invalid_formula(get_principal):
    with pytest.raises(ValueError):
        expression_service.update(
            expression=uuid.UUID(EXP1),
            principal=get_principal("owner"),
            formula="__import__('os')",
        )


def test_update_expression_clears_formula(get_principal):
    result = expression_service.update(
        expression=uuid.UUID(EXP1),
        principal=get_principal("owner"),
        formula=None,
    )
    assert result.formula is None


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
def test_delete_expression(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            expression_service.delete(
                expression=uuid.UUID(EXP1),
                principal=get_principal(principal),
            )
        assert error_fragment in _err(exc_info)
    else:
        expression_service.delete(
            expression=uuid.UUID(EXP1),
            principal=get_principal(principal),
        )
        assert not Expression.objects.filter(pk=uuid.UUID(EXP1)).exists()


def test_delete_expression_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        expression_service.delete(
            expression=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)