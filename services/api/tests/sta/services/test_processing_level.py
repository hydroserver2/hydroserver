import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from domains.sta.services import ProcessingLevelService
from interfaces.api.schemas import (
    ProcessingLevelPostBody,
    ProcessingLevelPatchBody,
    ProcessingLevelSummaryResponse,
)

processing_level_service = ProcessingLevelService()


@pytest.mark.parametrize(
    "principal, params, processing_level_codes, max_queries",
    [
        # Test user access
        (
            "owner",
            {},
            [
                "SystemProcessingLevel",
                "SystemAssignedProcessingLevel",
                "PublicProcessingLevel",
                "PublicAssignedProcessingLevel",
                "PrivateProcessingLevel",
                "PrivateAssignedProcessingLevel",
            ],
            3,
        ),
        (
            "editor",
            {},
            [
                "SystemProcessingLevel",
                "SystemAssignedProcessingLevel",
                "PublicProcessingLevel",
                "PublicAssignedProcessingLevel",
                "PrivateProcessingLevel",
                "PrivateAssignedProcessingLevel",
            ],
            3,
        ),
        (
            "viewer",
            {},
            [
                "SystemProcessingLevel",
                "SystemAssignedProcessingLevel",
                "PublicProcessingLevel",
                "PublicAssignedProcessingLevel",
                "PrivateProcessingLevel",
                "PrivateAssignedProcessingLevel",
            ],
            3,
        ),
        (
            "admin",
            {},
            [
                "SystemProcessingLevel",
                "SystemAssignedProcessingLevel",
                "PublicProcessingLevel",
                "PublicAssignedProcessingLevel",
                "PrivateProcessingLevel",
                "PrivateAssignedProcessingLevel",
            ],
            3,
        ),
        (
            "apikey",
            {},
            [
                "SystemProcessingLevel",
                "SystemAssignedProcessingLevel",
                "PublicProcessingLevel",
                "PublicAssignedProcessingLevel",
            ],
            4,
        ),
        (
            "unaffiliated",
            {},
            [
                "SystemProcessingLevel",
                "SystemAssignedProcessingLevel",
                "PublicProcessingLevel",
                "PublicAssignedProcessingLevel",
            ],
            3,
        ),
        (
            "anonymous",
            {},
            [
                "SystemProcessingLevel",
                "SystemAssignedProcessingLevel",
                "PublicProcessingLevel",
                "PublicAssignedProcessingLevel",
            ],
            3,
        ),
        # Test pagination and order_by
        (
            "owner",
            {"page": 2, "page_size": 2, "order_by": "-code"},
            [
                "PublicProcessingLevel",
                "PublicAssignedProcessingLevel",
            ],
            3,
        ),
        # Test filtering
        (
            "owner",
            {"workspace_id": "6e0deaf2-a92b-421b-9ece-86783265596f"},
            ["PublicProcessingLevel", "PublicAssignedProcessingLevel"],
            3,
        ),
        (
            "owner",
            {"datastreams__thing_id": "3b7818af-eff7-4149-8517-e5cad9dc22e1"},
            ["SystemAssignedProcessingLevel", "PublicAssignedProcessingLevel"],
            3,
        ),
        (
            "owner",
            {"datastreams__id": "27c70b41-e845-40ea-8cc7-d1b40f89816b"},
            ["PublicAssignedProcessingLevel"],
            3,
        ),
    ],
)
def test_list_processing_level(
    django_assert_num_queries,
    get_principal,
    principal,
    params,
    processing_level_codes,
    max_queries,
):
    with django_assert_num_queries(max_queries):
        http_response = HttpResponse()
        result = processing_level_service.list(
            principal=get_principal(principal),
            response=http_response,
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=[params.pop("order_by")] if "order_by" in params else [],
            filtering=params,
        )
        assert Counter(
            str(processing_level.code) for processing_level in result
        ) == Counter(processing_level_codes)
        assert (
            ProcessingLevelSummaryResponse.from_orm(processing_level)
            for processing_level in result
        )


@pytest.mark.parametrize(
    "principal, processing_level, message, error_code",
    [
        # Test public access
        (
            "owner",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "SystemProcessingLevel",
            None,
        ),
        (
            "owner",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "PublicProcessingLevel",
            None,
        ),
        (
            "admin",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "SystemProcessingLevel",
            None,
        ),
        (
            "admin",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "PublicProcessingLevel",
            None,
        ),
        (
            "editor",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "SystemProcessingLevel",
            None,
        ),
        (
            "editor",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "PublicProcessingLevel",
            None,
        ),
        (
            "viewer",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "SystemProcessingLevel",
            None,
        ),
        (
            "viewer",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "PublicProcessingLevel",
            None,
        ),
        (
            "apikey",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "SystemProcessingLevel",
            None,
        ),
        (
            "apikey",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "PublicProcessingLevel",
            None,
        ),
        (
            "unaffiliated",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "SystemProcessingLevel",
            None,
        ),
        (
            "unaffiliated",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "PublicProcessingLevel",
            None,
        ),
        (
            "anonymous",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "SystemProcessingLevel",
            None,
        ),
        (
            "anonymous",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "PublicProcessingLevel",
            None,
        ),
        # Test private access
        (
            "owner",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            "PrivateProcessingLevel",
            None,
        ),
        (
            "admin",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            "PrivateProcessingLevel",
            None,
        ),
        # Test unauthorized access
        (
            "apikey",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            "Processing level does not exist",
            404,
        ),
        (
            "unaffiliated",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            "Processing level does not exist",
            404,
        ),
        (
            "anonymous",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            "Processing level does not exist",
            404,
        ),
        # Test missing resource
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "Processing level does not exist",
            404,
        ),
    ],
)
def test_get_processing_level(
    get_principal, principal, processing_level, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            processing_level_service.get(
                principal=get_principal(principal), uid=uuid.UUID(processing_level)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        processing_level_get = processing_level_service.get(
            principal=get_principal(principal), uid=uuid.UUID(processing_level)
        )
        assert processing_level_get.code == message
        assert ProcessingLevelSummaryResponse.from_orm(processing_level_get)


@pytest.mark.parametrize(
    "principal, processing_level_fields, message, error_code",
    [
        # Test create valid ProcessingLevel
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
        # Test create invalid ProcessingLevel
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
def test_create_processing_level(
    get_principal, principal, processing_level_fields, message, error_code
):
    processing_level_data = ProcessingLevelPostBody(
        code=processing_level_fields.get("code", "New"),
        definition=processing_level_fields.get("definition", "New"),
        explanation=processing_level_fields.get("explanation", "New"),
        workspace_id=(
            (
                uuid.UUID(wid)
                if (wid := processing_level_fields["workspace_id"]) is not None
                else None
            )
            if "workspace_id" in processing_level_fields
            else uuid.UUID("6e0deaf2-a92b-421b-9ece-86783265596f")
        ),
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            processing_level_service.create(
                principal=get_principal(principal), data=processing_level_data
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        processing_level_create = processing_level_service.create(
            principal=get_principal(principal), data=processing_level_data
        )
        assert processing_level_create.code == processing_level_data.code
        assert processing_level_create.definition == processing_level_data.definition
        assert processing_level_create.explanation == processing_level_data.explanation
        assert ProcessingLevelSummaryResponse.from_orm(processing_level_create)


@pytest.mark.parametrize(
    "principal, processing_level, processing_level_fields, message, error_code",
    [
        # Test edit ProcessingLevel
        ("owner", "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575", {}, None, None),
        ("editor", "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575", {}, None, None),
        ("admin", "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575", {}, None, None),
        # Test unauthorized attempts
        (
            "viewer",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            {},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            {},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            {},
            "Processing level does not exist",
            404,
        ),
        (
            "unaffiliated",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            {},
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            {},
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            {},
            "Processing level does not exist",
            404,
        ),
        (
            "anonymous",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            {},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            {},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            {},
            "Processing level does not exist",
            404,
        ),
    ],
)
def test_edit_processing_level(
    get_principal,
    principal,
    processing_level,
    processing_level_fields,
    message,
    error_code,
):
    processing_level_data = ProcessingLevelPatchBody(
        code=processing_level_fields.get("code", "New"),
        definition=processing_level_fields.get("definition", "New"),
        explanation=processing_level_fields.get("explanation", "New"),
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            processing_level_service.update(
                principal=get_principal(principal),
                uid=uuid.UUID(processing_level),
                data=processing_level_data,
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        processing_level_update = processing_level_service.update(
            principal=get_principal(principal),
            uid=uuid.UUID(processing_level),
            data=processing_level_data,
        )
        assert processing_level_update.code == processing_level_data.code
        assert processing_level_update.definition == processing_level_data.definition
        assert processing_level_update.explanation == processing_level_data.explanation
        assert ProcessingLevelSummaryResponse.from_orm(processing_level_update)


@pytest.mark.parametrize(
    "principal, processing_level, message, error_code",
    [
        # Test delete ProcessingLevel
        ("owner", "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575", None, None),
        ("editor", "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575", None, None),
        ("admin", "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575", None, None),
        # Test unauthorized attempts
        (
            "viewer",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            "Processing level does not exist",
            404,
        ),
        (
            "unaffiliated",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            "Processing level does not exist",
            404,
        ),
        (
            "anonymous",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            "Processing level does not exist",
            404,
        ),
    ],
)
def test_delete_processing_level(
    get_principal, principal, processing_level, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            processing_level_service.delete(
                principal=get_principal(principal), uid=uuid.UUID(processing_level)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        processing_level_delete = processing_level_service.delete(
            principal=get_principal(principal), uid=uuid.UUID(processing_level)
        )
        assert processing_level_delete == "Processing level deleted"
