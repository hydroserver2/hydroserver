import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from domains.sta.services import UnitService
from interfaces.api.schemas import UnitPostBody, UnitPatchBody, UnitSummaryResponse

unit_service = UnitService()


@pytest.mark.parametrize(
    "principal, params, unit_names, max_queries",
    [
        # Test user access
        (
            "owner",
            {},
            [
                "System Unit",
                "System Assigned Unit",
                "Public Unit",
                "Public Assigned Unit",
                "Private Unit",
                "Private Assigned Unit",
            ],
            3,
        ),
        (
            "editor",
            {},
            [
                "System Unit",
                "System Assigned Unit",
                "Public Unit",
                "Public Assigned Unit",
                "Private Unit",
                "Private Assigned Unit",
            ],
            3,
        ),
        (
            "viewer",
            {},
            [
                "System Unit",
                "System Assigned Unit",
                "Public Unit",
                "Public Assigned Unit",
                "Private Unit",
                "Private Assigned Unit",
            ],
            3,
        ),
        (
            "admin",
            {},
            [
                "System Unit",
                "System Assigned Unit",
                "Public Unit",
                "Public Assigned Unit",
                "Private Unit",
                "Private Assigned Unit",
            ],
            3,
        ),
        (
            "apikey",
            {},
            [
                "System Unit",
                "System Assigned Unit",
                "Public Unit",
                "Public Assigned Unit",
            ],
            4,
        ),
        (
            "unaffiliated",
            {},
            [
                "System Unit",
                "System Assigned Unit",
                "Public Unit",
                "Public Assigned Unit",
            ],
            3,
        ),
        (
            "anonymous",
            {},
            [
                "System Unit",
                "System Assigned Unit",
                "Public Unit",
                "Public Assigned Unit",
            ],
            3,
        ),
        # Test pagination and order_by
        (
            "owner",
            {"page": 2, "page_size": 2, "order_by": "-name"},
            [
                "Public Unit",
                "Public Assigned Unit",
            ],
            3,
        ),
        # Test filtering
        (
            "owner",
            {"workspace_id": "6e0deaf2-a92b-421b-9ece-86783265596f"},
            ["Public Unit", "Public Assigned Unit"],
            3,
        ),
        (
            "owner",
            {"datastreams__thing_id": "3b7818af-eff7-4149-8517-e5cad9dc22e1"},
            ["System Assigned Unit", "Public Assigned Unit"],
            3,
        ),
        (
            "owner",
            {"datastreams__id": "27c70b41-e845-40ea-8cc7-d1b40f89816b"},
            ["Public Assigned Unit"],
            3,
        ),
        ("owner", {"unit_type": "System Unit"}, ["System Unit"], 3),
    ],
)
def test_list_unit(
    django_assert_num_queries, get_principal, principal, params, unit_names, max_queries
):
    with django_assert_num_queries(max_queries):
        http_response = HttpResponse()
        result = unit_service.list(
            principal=get_principal(principal),
            response=http_response,
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=[params.pop("order_by")] if "order_by" in params else [],
            filtering=params,
        )
        assert Counter(str(unit.name) for unit in result) == Counter(unit_names)
        assert (UnitSummaryResponse.from_orm(unit) for unit in result)


@pytest.mark.parametrize(
    "principal, unit, message, error_code",
    [
        # Test public access
        ("owner", "2ca850fa-ce19-4d8a-9dfd-8d54a261778d", "System Unit", None),
        ("owner", "fe3799b7-f061-42f2-b012-b569303f8a41", "Public Unit", None),
        ("admin", "2ca850fa-ce19-4d8a-9dfd-8d54a261778d", "System Unit", None),
        ("admin", "fe3799b7-f061-42f2-b012-b569303f8a41", "Public Unit", None),
        ("editor", "2ca850fa-ce19-4d8a-9dfd-8d54a261778d", "System Unit", None),
        ("editor", "fe3799b7-f061-42f2-b012-b569303f8a41", "Public Unit", None),
        ("viewer", "2ca850fa-ce19-4d8a-9dfd-8d54a261778d", "System Unit", None),
        ("viewer", "fe3799b7-f061-42f2-b012-b569303f8a41", "Public Unit", None),
        ("apikey", "2ca850fa-ce19-4d8a-9dfd-8d54a261778d", "System Unit", None),
        ("apikey", "fe3799b7-f061-42f2-b012-b569303f8a41", "Public Unit", None),
        ("unaffiliated", "2ca850fa-ce19-4d8a-9dfd-8d54a261778d", "System Unit", None),
        ("unaffiliated", "fe3799b7-f061-42f2-b012-b569303f8a41", "Public Unit", None),
        ("anonymous", "2ca850fa-ce19-4d8a-9dfd-8d54a261778d", "System Unit", None),
        ("anonymous", "fe3799b7-f061-42f2-b012-b569303f8a41", "Public Unit", None),
        # Test private access
        ("owner", "98a74429-2be2-44c0-8f7f-2df2ca12893d", "Private Unit", None),
        ("admin", "98a74429-2be2-44c0-8f7f-2df2ca12893d", "Private Unit", None),
        # Test unauthorized access
        (
            "apikey",
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            "Unit does not exist",
            404,
        ),
        (
            "unaffiliated",
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            "Unit does not exist",
            404,
        ),
        (
            "anonymous",
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            "Unit does not exist",
            404,
        ),
        # Test missing resource
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "Unit does not exist",
            404,
        ),
    ],
)
def test_get_unit(get_principal, principal, unit, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            unit_service.get(principal=get_principal(principal), uid=uuid.UUID(unit))
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        unit_get = unit_service.get(
            principal=get_principal(principal), uid=uuid.UUID(unit)
        )
        assert unit_get.name == message
        assert UnitSummaryResponse.from_orm(unit_get)


@pytest.mark.parametrize(
    "principal, unit_fields, message, error_code",
    [
        # Test create valid Unit
        ("owner", {}, None, None),
        ("owner", {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"}, None, None),
        ("editor", {}, None, None),
        (
            "editor",
            {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"},
            None,
            None,
        ),
        ("admin", {}, None, None),
        ("admin", {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"}, None, None),
        ("admin", {"workspace_id": None}, None, None),
        # Test create invalid Unit
        (
            "owner",
            {"workspace_id": "00000000-0000-0000-0000-000000000000"},
            "Workspace does not exist",
            404,
        ),
        # Test unauthorized attempts
        ("owner", {"workspace_id": None}, "You do not have permission", 403),
        ("viewer", {}, "You do not have permission", 403),
        (
            "viewer",
            {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"},
            "You do not have permission",
            403,
        ),
        ("apikey", {}, "You do not have permission", 403),
        (
            "apikey",
            {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"},
            "Workspace does not exist",
            404,
        ),
        ("unaffiliated", {}, "You do not have permission", 403),
        (
            "unaffiliated",
            {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"},
            "Workspace does not exist",
            404,
        ),
        ("anonymous", {}, "You do not have permission", 403),
        (
            "anonymous",
            {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"},
            "Workspace does not exist",
            404,
        ),
    ],
)
def test_create_unit(get_principal, principal, unit_fields, message, error_code):
    unit_data = UnitPostBody(
        name=unit_fields.get("name", "New"),
        symbol=unit_fields.get("symbol", "New"),
        definition=unit_fields.get("definition", "New"),
        unit_type=unit_fields.get("unit_type", "New"),
        workspace_id=(
            (
                uuid.UUID(wid)
                if (wid := unit_fields["workspace_id"]) is not None
                else None
            )
            if "workspace_id" in unit_fields
            else uuid.UUID("6e0deaf2-a92b-421b-9ece-86783265596f")
        ),
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            unit_service.create(principal=get_principal(principal), data=unit_data)
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        unit_create = unit_service.create(
            principal=get_principal(principal), data=unit_data
        )
        assert unit_create.symbol == unit_data.symbol
        assert unit_create.name == unit_data.name
        assert unit_create.definition == unit_data.definition
        assert unit_create.unit_type == unit_data.unit_type
        assert UnitSummaryResponse.from_orm(unit_create)


@pytest.mark.parametrize(
    "principal, unit, unit_fields, message, error_code",
    [
        # Test edit Unit
        ("owner", "fe3799b7-f061-42f2-b012-b569303f8a41", {}, None, None),
        ("editor", "fe3799b7-f061-42f2-b012-b569303f8a41", {}, None, None),
        ("admin", "fe3799b7-f061-42f2-b012-b569303f8a41", {}, None, None),
        # Test unauthorized attempts
        (
            "viewer",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            {},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            {},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            {},
            "Unit does not exist",
            404,
        ),
        (
            "unaffiliated",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            {},
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            {},
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            {},
            "Unit does not exist",
            404,
        ),
        (
            "anonymous",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            {},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            {},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            {},
            "Unit does not exist",
            404,
        ),
    ],
)
def test_edit_unit(get_principal, principal, unit, unit_fields, message, error_code):
    unit_data = UnitPatchBody(
        name=unit_fields.get("name", "New"),
        symbol=unit_fields.get("symbol", "New"),
        definition=unit_fields.get("definition", "New"),
        unit_type=unit_fields.get("unit_type", "New"),
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            unit_service.update(
                principal=get_principal(principal), uid=uuid.UUID(unit), data=unit_data
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        unit_update = unit_service.update(
            principal=get_principal(principal), uid=uuid.UUID(unit), data=unit_data
        )
        assert unit_update.definition == unit_data.definition
        assert unit_update.name == unit_data.name
        assert unit_update.symbol == unit_data.symbol
        assert unit_update.unit_type == unit_data.unit_type
        assert UnitSummaryResponse.from_orm(unit_update)


@pytest.mark.parametrize(
    "principal, unit, message, error_code",
    [
        # Test delete Unit
        ("owner", "fe3799b7-f061-42f2-b012-b569303f8a41", None, None),
        ("editor", "fe3799b7-f061-42f2-b012-b569303f8a41", None, None),
        ("admin", "fe3799b7-f061-42f2-b012-b569303f8a41", None, None),
        # Test unauthorized attempts
        (
            "viewer",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "You do not have permission",
            403,
        ),
        ("apikey", "98a74429-2be2-44c0-8f7f-2df2ca12893d", "Unit does not exist", 404),
        (
            "unaffiliated",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            "Unit does not exist",
            404,
        ),
        (
            "anonymous",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            "Unit does not exist",
            404,
        ),
    ],
)
def test_delete_unit(get_principal, principal, unit, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            unit_service.delete(principal=get_principal(principal), uid=uuid.UUID(unit))
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        unit_delete = unit_service.delete(
            principal=get_principal(principal), uid=uuid.UUID(unit)
        )
        assert unit_delete == "Unit deleted"
