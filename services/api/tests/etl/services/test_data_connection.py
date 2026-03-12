import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from domains.etl.services import DataConnectionService
from interfaces.api.schemas import (
    DataConnectionPostBody,
    DataConnectionPatchBody,
    DataConnectionSummaryResponse,
    DataConnectionDetailResponse
)

data_connection_service = DataConnectionService()


@pytest.mark.parametrize(
    "principal, params, data_connection_names, max_queries",
    [
        # Test user access
        (
            "owner",
            {},
            ["Test ETL Data Connection", "Test Global ETL Data Connection"],
            4,
        ),
        (
            "editor",
            {},
            ["Test ETL Data Connection", "Test Global ETL Data Connection"],
            4,
        ),
        (
            "viewer",
            {},
            ["Test ETL Data Connection", "Test Global ETL Data Connection"],
            4,
        ),
        (
            "admin",
            {},
            ["Test ETL Data Connection", "Test Global ETL Data Connection"],
            4,
        ),
        ("apikey", {}, ["Test Global ETL Data Connection"], 4),
        ("unaffiliated", {}, ["Test Global ETL Data Connection"], 4),
        ("anonymous", {}, ["Test Global ETL Data Connection"], 4),
        # Test pagination and order_by
        (
            "owner",
            {"page": 3, "page_size": 1, "order_by": "-name"},
            [],
            4,
        ),
        # Test filtering
        (
            "owner",
            {"data_connection_type": "SDL"},
            ["Test ETL Data Connection"],
            4,
        ),
    ],
)
def test_list_data_connection(
    django_assert_max_num_queries,
    get_principal,
    principal,
    params,
    data_connection_names,
    max_queries,
):
    with django_assert_max_num_queries(max_queries):
        http_response = HttpResponse()
        result = data_connection_service.list(
            principal=get_principal(principal),
            response=http_response,
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=[params.pop("order_by")] if "order_by" in params else [],
            filtering=params,
        )
        assert Counter(
            str(data_connection.name) for data_connection in result
        ) == Counter(data_connection_names)
        assert (
            DataConnectionSummaryResponse.from_orm(data_connection)
            for data_connection in result
        )


@pytest.mark.parametrize(
    "principal, data_connection, message, error_code",
    [
        (
            "owner",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "Test ETL Data Connection",
            None,
        ),
        (
            "admin",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "Test ETL Data Connection",
            None,
        ),
        (
            "editor",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "Test ETL Data Connection",
            None,
        ),
        (
            "viewer",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "Test ETL Data Connection",
            None,
        ),
        (
            "apikey",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            "anonymous",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            "anonymous",
            "019bbd9d-ee62-7669-8db0-3ef50802f1d8",
            "Test Global ETL Data Connection",
            None,
        ),
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            None,
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            None,
            "00000000-0000-0000-0000-000000000000",
            "ETL Data Connection does not exist",
            404,
        ),
    ],
)
def test_get_data_connection(
    get_principal, principal, data_connection, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            data_connection_service.get(
                principal=get_principal(principal), uid=uuid.UUID(data_connection)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        data_connection_get = data_connection_service.get(
            principal=get_principal(principal), uid=uuid.UUID(data_connection)
        )
        assert data_connection_get.name == message
        assert DataConnectionSummaryResponse.from_orm(data_connection_get)


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
def test_create_data_connection(
    get_principal, principal, workspace, message, error_code
):
    data_connection_data = DataConnectionPostBody(
        name="New", workspace_id=uuid.UUID(workspace), data_connection_type="Test", extractor=None, transformer=None, loader=None
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            data_connection_service.create(
                principal=get_principal(principal), data=data_connection_data
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        data_connection_create = data_connection_service.create(
            principal=get_principal(principal), data=data_connection_data
        )
        assert data_connection_create.name == data_connection_data.name
        assert DataConnectionDetailResponse.from_orm(data_connection_create)


@pytest.mark.parametrize(
    "principal, data_connection, message, error_code",
    [
        ("admin", "019adb5c-da8b-7970-877d-c3b4ca37cc60", None, None),
        ("admin", "019adb5c-da8b-7970-877d-c3b4ca37cc60", None, None),
        ("owner", "019adb5c-da8b-7970-877d-c3b4ca37cc60", None, None),
        ("owner", "019adb5c-da8b-7970-877d-c3b4ca37cc60", None, None),
        ("editor", "019adb5c-da8b-7970-877d-c3b4ca37cc60", None, None),
        ("editor", "019adb5c-da8b-7970-877d-c3b4ca37cc60", None, None),
        (
            "viewer",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            "apikey",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            "anonymous",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            "anonymous",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            None,
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            None,
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            None,
            "00000000-0000-0000-0000-000000000000",
            "ETL Data Connection does not exist",
            404,
        ),
    ],
)
def test_edit_data_connection(
    get_principal, principal, data_connection, message, error_code
):
    data_connection_data = DataConnectionPatchBody(
        name="New", data_connection_type="Test"
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            data_connection_service.update(
                principal=get_principal(principal),
                uid=uuid.UUID(data_connection),
                data=data_connection_data,
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        data_connection_update = data_connection_service.update(
            principal=get_principal(principal),
            uid=uuid.UUID(data_connection),
            data=data_connection_data,
        )
        assert data_connection_update.name == data_connection_data.name
        assert DataConnectionDetailResponse.from_orm(data_connection_update)


@pytest.mark.parametrize(
    "principal, data_connection, message, error_code",
    [
        ("admin", "019adb5c-da8b-7970-877d-c3b4ca37cc60", None, None),
        ("admin", "019adb5c-da8b-7970-877d-c3b4ca37cc60", None, None),
        ("owner", "019adb5c-da8b-7970-877d-c3b4ca37cc60", None, None),
        ("owner", "019adb5c-da8b-7970-877d-c3b4ca37cc60", None, None),
        ("editor", "019adb5c-da8b-7970-877d-c3b4ca37cc60", None, None),
        ("editor", "019adb5c-da8b-7970-877d-c3b4ca37cc60", None, None),
        (
            "viewer",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            "apikey",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            "anonymous",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            "anonymous",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            None,
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            None,
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "ETL Data Connection does not exist",
            404,
        ),
        (
            None,
            "00000000-0000-0000-0000-000000000000",
            "ETL Data Connection does not exist",
            404,
        ),
    ],
)
def test_delete_data_connection(
    get_principal, principal, data_connection, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            data_connection_service.delete(
                principal=get_principal(principal), uid=uuid.UUID(data_connection)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        data_connection_delete = data_connection_service.delete(
            principal=get_principal(principal), uid=uuid.UUID(data_connection)
        )
        assert data_connection_delete == "ETL Data Connection deleted"
