import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from domains.sta.services import ResultQualifierService
from interfaces.api.schemas import (
    ResultQualifierPostBody,
    ResultQualifierPatchBody,
    ResultQualifierSummaryResponse,
)

result_qualifier_service = ResultQualifierService()


@pytest.mark.parametrize(
    "principal, params, result_qualifier_codes, max_queries",
    [
        # Test user access
        (
            "owner",
            {},
            [
                "SystemResultQualifier",
                "PublicResultQualifier",
                "PrivateResultQualifier",
            ],
            3,
        ),
        (
            "editor",
            {},
            [
                "SystemResultQualifier",
                "PublicResultQualifier",
                "PrivateResultQualifier",
            ],
            3,
        ),
        (
            "viewer",
            {},
            [
                "SystemResultQualifier",
                "PublicResultQualifier",
                "PrivateResultQualifier",
            ],
            3,
        ),
        (
            "admin",
            {},
            [
                "SystemResultQualifier",
                "PublicResultQualifier",
                "PrivateResultQualifier",
            ],
            3,
        ),
        ("apikey", {}, ["SystemResultQualifier", "PublicResultQualifier"], 4),
        ("unaffiliated", {}, ["SystemResultQualifier", "PublicResultQualifier"], 3),
        ("anonymous", {}, ["SystemResultQualifier", "PublicResultQualifier"], 3),
        # Test pagination and order_by
        (
            "owner",
            {"page": 2, "page_size": 2, "order_by": "-code"},
            ["PrivateResultQualifier"],
            3,
        ),
        # Test filtering
        (
            "owner",
            {"workspace_id": "6e0deaf2-a92b-421b-9ece-86783265596f"},
            ["PublicResultQualifier"],
            3,
        ),
    ],
)
def test_list_result_qualifier(
    django_assert_num_queries,
    get_principal,
    principal,
    params,
    result_qualifier_codes,
    max_queries,
):
    with django_assert_num_queries(max_queries):
        http_response = HttpResponse()
        result = result_qualifier_service.list(
            principal=get_principal(principal),
            response=http_response,
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=[params.pop("order_by")] if "order_by" in params else [],
            filtering=params,
        )
        assert Counter(
            str(result_qualifier.code) for result_qualifier in result
        ) == Counter(result_qualifier_codes)
        assert (
            ResultQualifierSummaryResponse.from_orm(result_qualifier)
            for result_qualifier in result
        )


@pytest.mark.parametrize(
    "principal, result_qualifier, message, error_code",
    [
        # Test public access
        (
            "owner",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            "SystemResultQualifier",
            None,
        ),
        (
            "owner",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            "PublicResultQualifier",
            None,
        ),
        (
            "admin",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            "SystemResultQualifier",
            None,
        ),
        (
            "admin",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            "PublicResultQualifier",
            None,
        ),
        (
            "editor",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            "SystemResultQualifier",
            None,
        ),
        (
            "editor",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            "PublicResultQualifier",
            None,
        ),
        (
            "viewer",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            "SystemResultQualifier",
            None,
        ),
        (
            "viewer",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            "PublicResultQualifier",
            None,
        ),
        (
            "apikey",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            "SystemResultQualifier",
            None,
        ),
        (
            "apikey",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            "PublicResultQualifier",
            None,
        ),
        (
            "unaffiliated",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            "SystemResultQualifier",
            None,
        ),
        (
            "unaffiliated",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            "PublicResultQualifier",
            None,
        ),
        (
            "anonymous",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            "SystemResultQualifier",
            None,
        ),
        (
            "anonymous",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            "PublicResultQualifier",
            None,
        ),
        # Test private access
        (
            "owner",
            "932dffca-0277-4dc2-8129-cb10212c4185",
            "PrivateResultQualifier",
            None,
        ),
        (
            "admin",
            "932dffca-0277-4dc2-8129-cb10212c4185",
            "PrivateResultQualifier",
            None,
        ),
        # Test unauthorized access
        (
            "apikey",
            "932dffca-0277-4dc2-8129-cb10212c4185",
            "Result qualifier does not exist",
            404,
        ),
        (
            "unaffiliated",
            "932dffca-0277-4dc2-8129-cb10212c4185",
            "Result qualifier does not exist",
            404,
        ),
        (
            "anonymous",
            "932dffca-0277-4dc2-8129-cb10212c4185",
            "Result qualifier does not exist",
            404,
        ),
        # Test missing resource
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "Result qualifier does not exist",
            404,
        ),
    ],
)
def test_get_result_qualifier(
    get_principal, principal, result_qualifier, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            result_qualifier_service.get(
                principal=get_principal(principal), uid=uuid.UUID(result_qualifier)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        result_qualifier_get = result_qualifier_service.get(
            principal=get_principal(principal), uid=uuid.UUID(result_qualifier)
        )
        assert result_qualifier_get.code == message
        assert ResultQualifierSummaryResponse.from_orm(result_qualifier_get)


@pytest.mark.parametrize(
    "principal, result_qualifier_fields, message, error_code",
    [
        # Test create valid Result Qualifier
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
        # Test create invalid Result Qualifier
        (
            "owner",
            {"workspace_id": "00000000-0000-0000-0000-000000000000"},
            "Workspace does not exist",
            404,
        ),
        (
            "owner",
            {
                "workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10",
                "code": "PrivateResultQualifier",
            },
            "A result qualifier with this ID or code already exists",
            409,
        ),
        (
            "admin",
            {"workspace_id": None, "code": "SystemResultQualifier"},
            "A result qualifier with this ID or code already exists",
            409,
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
def test_create_result_qualifier(
    get_principal, principal, result_qualifier_fields, message, error_code
):
    result_qualifier_data = ResultQualifierPostBody(
        code=result_qualifier_fields.get("code", "New"),
        description=result_qualifier_fields.get("description", "New"),
        workspace_id=(
            (
                uuid.UUID(wid)
                if (wid := result_qualifier_fields["workspace_id"]) is not None
                else None
            )
            if "workspace_id" in result_qualifier_fields
            else uuid.UUID("6e0deaf2-a92b-421b-9ece-86783265596f")
        ),
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            result_qualifier_service.create(
                principal=get_principal(principal), data=result_qualifier_data
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        result_qualifier_create = result_qualifier_service.create(
            principal=get_principal(principal), data=result_qualifier_data
        )
        assert result_qualifier_create.code == result_qualifier_data.code
        assert result_qualifier_create.description == result_qualifier_data.description
        assert ResultQualifierSummaryResponse.from_orm(result_qualifier_create)


@pytest.mark.parametrize(
    "principal, result_qualifier, result_qualifier_fields, message, error_code",
    [
        # Test edit Result Qualifier
        ("owner", "c66e9597-f474-4a77-afa0-f2b5a673249e", {}, None, None),
        ("editor", "c66e9597-f474-4a77-afa0-f2b5a673249e", {}, None, None),
        ("admin", "c66e9597-f474-4a77-afa0-f2b5a673249e", {}, None, None),
        # Test unauthorized attempts
        (
            "viewer",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            {},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            {},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "932dffca-0277-4dc2-8129-cb10212c4185",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "932dffca-0277-4dc2-8129-cb10212c4185",
            {},
            "Result qualifier does not exist",
            404,
        ),
        (
            "unaffiliated",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            {},
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            {},
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "932dffca-0277-4dc2-8129-cb10212c4185",
            {},
            "Result qualifier does not exist",
            404,
        ),
        (
            "anonymous",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            {},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            {},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "932dffca-0277-4dc2-8129-cb10212c4185",
            {},
            "Result qualifier does not exist",
            404,
        ),
    ],
)
def test_edit_result_qualifier(
    get_principal,
    principal,
    result_qualifier,
    result_qualifier_fields,
    message,
    error_code,
):
    result_qualifier_data = ResultQualifierPatchBody(
        code=result_qualifier_fields.get("code", "New"),
        description=result_qualifier_fields.get("description", "New"),
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            result_qualifier_service.update(
                principal=get_principal(principal),
                uid=uuid.UUID(result_qualifier),
                data=result_qualifier_data,
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        result_qualifier_update = result_qualifier_service.update(
            principal=get_principal(principal),
            uid=uuid.UUID(result_qualifier),
            data=result_qualifier_data,
        )
        assert result_qualifier_update.code == result_qualifier_data.code
        assert result_qualifier_update.description == result_qualifier_data.description
        assert ResultQualifierSummaryResponse.from_orm(result_qualifier_update)


@pytest.mark.parametrize(
    "principal, result_qualifier, message, error_code",
    [
        # Test delete Result Qualifier
        ("owner", "c66e9597-f474-4a77-afa0-f2b5a673249e", None, None),
        ("editor", "c66e9597-f474-4a77-afa0-f2b5a673249e", None, None),
        ("admin", "c66e9597-f474-4a77-afa0-f2b5a673249e", None, None),
        # Test unauthorized attempts
        (
            "viewer",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "932dffca-0277-4dc2-8129-cb10212c4185",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "932dffca-0277-4dc2-8129-cb10212c4185",
            "Result qualifier does not exist",
            404,
        ),
        (
            "unaffiliated",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "932dffca-0277-4dc2-8129-cb10212c4185",
            "Result qualifier does not exist",
            404,
        ),
        (
            "anonymous",
            "c66e9597-f474-4a77-afa0-f2b5a673249e",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "667b63fb-e7a9-4b10-b6d8-9a4bafdf11bf",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "932dffca-0277-4dc2-8129-cb10212c4185",
            "Result qualifier does not exist",
            404,
        ),
    ],
)
def test_delete_result_qualifier(
    get_principal, principal, result_qualifier, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            result_qualifier_service.delete(
                principal=get_principal(principal), uid=uuid.UUID(result_qualifier)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        result_qualifier_delete = result_qualifier_service.delete(
            principal=get_principal(principal), uid=uuid.UUID(result_qualifier)
        )
        assert result_qualifier_delete == "Result qualifier deleted"
