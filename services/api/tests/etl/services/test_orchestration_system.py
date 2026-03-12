import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from domains.etl.services import OrchestrationSystemService
from interfaces.api.schemas import (
    OrchestrationSystemPostBody,
    OrchestrationSystemPatchBody,
    OrchestrationSystemSummaryResponse,
    OrchestrationSystemDetailResponse
)

orchestration_system_service = OrchestrationSystemService()


@pytest.mark.parametrize(
    "principal, params, orchestration_system_names, max_queries",
    [
        # Test user access
        (
            "owner",
            {},
            ["HydroServer", "Test Streaming Data Loader"],
            4,
        ),
        (
            "editor",
            {},
            ["HydroServer", "Test Streaming Data Loader"],
            4,
        ),
        (
            "viewer",
            {},
            ["HydroServer", "Test Streaming Data Loader"],
            4,
        ),
        (
            "admin",
            {},
            ["HydroServer", "Test Streaming Data Loader"],
            4,
        ),
        ("apikey", {}, ["HydroServer"], 4),
        ("unaffiliated", {}, ["HydroServer"], 4),
        ("anonymous", {}, ["HydroServer"], 4),
        # Test pagination and order_by
        (
            "owner",
            {"page": 2, "page_size": 1, "order_by": "-name"},
            ["HydroServer"],
            4,
        ),
        # Test filtering
        (
            "owner",
            {"orchestration_system_type": "SDL"},
            ["Test Streaming Data Loader"],
            4,
        ),
    ],
)
def test_list_orchestration_system(
    django_assert_max_num_queries,
    get_principal,
    principal,
    params,
    orchestration_system_names,
    max_queries,
):
    with django_assert_max_num_queries(max_queries):
        http_response = HttpResponse()
        result = orchestration_system_service.list(
            principal=get_principal(principal),
            response=http_response,
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=[params.pop("order_by")] if "order_by" in params else [],
            filtering=params,
        )
        assert Counter(
            str(orchestration_system.name) for orchestration_system in result
        ) == Counter(orchestration_system_names)
        assert (
            OrchestrationSystemSummaryResponse.from_orm(orchestration_system)
            for orchestration_system in result
        )


@pytest.mark.parametrize(
    "principal, orchestration_system, message, error_code",
    [
        (
            "owner",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Test Streaming Data Loader",
            None,
        ),
        (
            "admin",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Test Streaming Data Loader",
            None,
        ),
        (
            "editor",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Test Streaming Data Loader",
            None,
        ),
        (
            "viewer",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Test Streaming Data Loader",
            None,
        ),
        (
            "apikey",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            "anonymous",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "Orchestration system does not exist",
            404,
        ),
        (
            None,
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            None,
            "00000000-0000-0000-0000-000000000000",
            "Orchestration system does not exist",
            404,
        ),
    ],
)
def test_get_orchestration_system(
    get_principal, principal, orchestration_system, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            orchestration_system_service.get(
                principal=get_principal(principal), uid=uuid.UUID(orchestration_system)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        orchestration_system_get = orchestration_system_service.get(
            principal=get_principal(principal), uid=uuid.UUID(orchestration_system)
        )
        assert orchestration_system_get.name == message
        assert OrchestrationSystemSummaryResponse.from_orm(orchestration_system_get)


@pytest.mark.parametrize(
    "principal, workspace, message, error_code",
    [
        (
            "admin",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            None,
            None,
        ),
        (
            "admin",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            None,
            None,
        ),
        (
            "admin",
            "00000000-0000-0000-0000-000000000000",
            "Workspace does not exist",
            404,
        ),
        (
            "owner",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            None,
            None,
        ),
        (
            "owner",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            None,
            None,
        ),
        (
            "editor",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            None,
            None,
        ),
        (
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            None,
            None,
        ),
        (
            "viewer",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            None,
            None,
        ),
        (
            "apikey",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            "anonymous",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "Workspace does not exist",
            404,
        ),
        (
            None,
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "You do not have permission",
            403,
        ),
        (
            None,
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            None,
            "00000000-0000-0000-0000-000000000000",
            "Workspace does not exist",
            404,
        ),
    ],
)
def test_create_orchestration_system(
    get_principal, principal, workspace, message, error_code
):
    orchestration_system_data = OrchestrationSystemPostBody(
        name="New", workspace_id=uuid.UUID(workspace), orchestration_system_type="Test"
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            orchestration_system_service.create(
                principal=get_principal(principal), data=orchestration_system_data
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        orchestration_system_create = orchestration_system_service.create(
            principal=get_principal(principal), data=orchestration_system_data
        )
        assert orchestration_system_create.name == orchestration_system_data.name
        assert OrchestrationSystemDetailResponse.from_orm(orchestration_system_create)


@pytest.mark.parametrize(
    "principal, orchestration_system, message, error_code",
    [
        ("admin", "7cb900d2-eb11-4a59-a05b-dd02d95af312", None, None),
        ("admin", "7cb900d2-eb11-4a59-a05b-dd02d95af312", None, None),
        ("owner", "7cb900d2-eb11-4a59-a05b-dd02d95af312", None, None),
        ("owner", "7cb900d2-eb11-4a59-a05b-dd02d95af312", None, None),
        ("editor", "7cb900d2-eb11-4a59-a05b-dd02d95af312", None, None),
        ("editor", "7cb900d2-eb11-4a59-a05b-dd02d95af312", None, None),
        (
            "viewer",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            "apikey",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            "anonymous",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            "anonymous",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "Orchestration system does not exist",
            404,
        ),
        (
            None,
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            None,
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            None,
            "00000000-0000-0000-0000-000000000000",
            "Orchestration system does not exist",
            404,
        ),
    ],
)
def test_edit_orchestration_system(
    get_principal, principal, orchestration_system, message, error_code
):
    orchestration_system_data = OrchestrationSystemPatchBody(
        name="New", orchestration_system_type="Test"
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            orchestration_system_service.update(
                principal=get_principal(principal),
                uid=uuid.UUID(orchestration_system),
                data=orchestration_system_data,
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        orchestration_system_update = orchestration_system_service.update(
            principal=get_principal(principal),
            uid=uuid.UUID(orchestration_system),
            data=orchestration_system_data,
        )
        assert orchestration_system_update.name == orchestration_system_data.name
        assert OrchestrationSystemDetailResponse.from_orm(orchestration_system_update)


@pytest.mark.parametrize(
    "principal, orchestration_system, message, error_code",
    [
        ("admin", "7cb900d2-eb11-4a59-a05b-dd02d95af312", None, None),
        ("admin", "7cb900d2-eb11-4a59-a05b-dd02d95af312", None, None),
        ("owner", "7cb900d2-eb11-4a59-a05b-dd02d95af312", None, None),
        ("owner", "7cb900d2-eb11-4a59-a05b-dd02d95af312", None, None),
        ("editor", "7cb900d2-eb11-4a59-a05b-dd02d95af312", None, None),
        ("editor", "7cb900d2-eb11-4a59-a05b-dd02d95af312", None, None),
        (
            "viewer",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            "apikey",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            "anonymous",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            "anonymous",
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "Orchestration system does not exist",
            404,
        ),
        (
            None,
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            None,
            "7cb900d2-eb11-4a59-a05b-dd02d95af312",
            "Orchestration system does not exist",
            404,
        ),
        (
            None,
            "00000000-0000-0000-0000-000000000000",
            "Orchestration system does not exist",
            404,
        ),
    ],
)
def test_delete_orchestration_system(
    get_principal, principal, orchestration_system, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            orchestration_system_service.delete(
                principal=get_principal(principal), uid=uuid.UUID(orchestration_system)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        orchestration_system_delete = orchestration_system_service.delete(
            principal=get_principal(principal), uid=uuid.UUID(orchestration_system)
        )
        assert orchestration_system_delete == "Orchestration system deleted"
