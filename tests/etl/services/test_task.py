import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from domains.etl.services import TaskService
from interfaces.api.schemas import (
    TaskPostBody,
    TaskPatchBody,
    TaskSummaryResponse,
    TaskDetailResponse,
    TaskSchedulePostBody,
    TaskMappingPostBody,
    TaskMappingPathPostBody
)

task_service = TaskService()


@pytest.mark.parametrize(
    "principal, params, task_names, max_queries",
    [
        # Test user access
        (
            "owner",
            {},
            ["Test ETL Task"],
            7,
        ),
        (
            "editor",
            {},
            ["Test ETL Task"],
            7,
        ),
        (
            "viewer",
            {},
            ["Test ETL Task"],
            7,
        ),
        (
            "admin",
            {},
            ["Test ETL Task"],
            7,
        ),
        ("apikey", {}, [], 4),
        ("unaffiliated", {}, [], 4),
        ("anonymous", {}, [], 4),
        # Test pagination and order_by
        (
            "owner",
            {"page": 2, "page_size": 1, "order_by": "-name"},
            [],
            7,
        ),
        # Test filtering
        (
            "owner",
            {"task_type": "SDL"},
            ["Test ETL Task"],
            7,
        ),
    ],
)
def test_list_task(
    django_assert_max_num_queries,
    get_principal,
    principal,
    params,
    task_names,
    max_queries,
):
    with django_assert_max_num_queries(max_queries):
        http_response = HttpResponse()
        result = task_service.list(
            principal=get_principal(principal),
            response=http_response,
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=[params.pop("order_by")] if "order_by" in params else [],
            filtering=params,
        )
        assert Counter(
            str(task["name"]) for task in result
        ) == Counter(task_names)
        assert (
            TaskSummaryResponse.from_orm(task)
            for task in result
        )


@pytest.mark.parametrize(
    "principal, task, message, error_code",
    [
        (
            "owner",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "Test ETL Task",
            None,
        ),
        (
            "admin",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "Test ETL Task",
            None,
        ),
        (
            "editor",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "Test ETL Task",
            None,
        ),
        (
            "viewer",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "Test ETL Task",
            None,
        ),
        (
            "apikey",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            "anonymous",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "ETL task does not exist",
            404,
        ),
        (
            None,
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            None,
            "00000000-0000-0000-0000-000000000000",
            "ETL task does not exist",
            404,
        ),
    ],
)
def test_get_task(
    get_principal, principal, task, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            task_service.get(
                principal=get_principal(principal), uid=uuid.UUID(task)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        task_get = task_service.get(
            principal=get_principal(principal), uid=uuid.UUID(task)
        )
        assert task_get["name"] == message
        assert TaskSummaryResponse.from_orm(task_get)


@pytest.mark.parametrize(
    "principal, workspace, data_connection, message, error_code",
    [
        (
            "admin",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            None,
            None,
        ),
        (
            "admin",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "00000000-0000-0000-0000-000000000000",
            "ETL Data Connection does not exist",
            400,
        ),
        (
            "admin",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "Task and data connection must belong to the same workspace.",
            400,
        ),
        (
            "owner",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            None,
            None,
        ),
        (
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            None,
            None,
        ),
        (
            "viewer",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "Workspace does not exist",
            404,
        ),
        (
            "anonymous",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "00000000-0000-0000-0000-000000000000",
            "You do not have permission",
            403,
        ),
        (
            None,
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "019adb5c-da8b-7970-877d-c3b4ca37cc60",
            "Workspace does not exist",
            404,
        ),
        (
            None,
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "00000000-0000-0000-0000-000000000000",
            "You do not have permission",
            403,
        ),
    ],
)
def test_create_task(
    get_principal, principal, workspace, data_connection, message, error_code
):
    task_data = TaskPostBody(
        name="New", workspace_id=uuid.UUID(workspace), data_connection_id=uuid.UUID(data_connection),
        orchestration_system_id=uuid.UUID("019aead4-df4e-7a08-a609-dbc96df6befe"),
        schedule=TaskSchedulePostBody(
            paused=True,
            crontab="* * * * *"
        ),
        mappings=[TaskMappingPostBody(
            source_identifier="test", paths=[TaskMappingPathPostBody(target_identifier="test")]
        )]
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            task_service.create(
                principal=get_principal(principal), data=task_data
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        task_create = task_service.create(
            principal=get_principal(principal), data=task_data
        )
        assert task_create["name"] == task_data.name
        assert TaskDetailResponse.from_orm(task_create)


@pytest.mark.parametrize(
    "principal, task, message, error_code",
    [
        ("admin", "019adbc3-35e8-7f25-bc68-171fb66d446e", None, None),
        ("admin", "019adbc3-35e8-7f25-bc68-171fb66d446e", None, None),
        ("owner", "019adbc3-35e8-7f25-bc68-171fb66d446e", None, None),
        ("owner", "019adbc3-35e8-7f25-bc68-171fb66d446e", None, None),
        ("editor", "019adbc3-35e8-7f25-bc68-171fb66d446e", None, None),
        ("editor", "019adbc3-35e8-7f25-bc68-171fb66d446e", None, None),
        (
            "viewer",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            "apikey",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            "anonymous",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            "anonymous",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "ETL task does not exist",
            404,
        ),
        (
            None,
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            None,
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            None,
            "00000000-0000-0000-0000-000000000000",
            "ETL task does not exist",
            404,
        ),
    ],
)
def test_edit_task(
    get_principal, principal, task, message, error_code
):
    task_data = TaskPatchBody(
        name="New"
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            task_service.update(
                principal=get_principal(principal),
                uid=uuid.UUID(task),
                data=task_data,
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        task_update = task_service.update(
            principal=get_principal(principal),
            uid=uuid.UUID(task),
            data=task_data,
        )
        assert task_update["name"] == task_data.name
        assert TaskDetailResponse.from_orm(task_update)


@pytest.mark.parametrize(
    "principal, task, message, error_code",
    [
        ("admin", "019adbc3-35e8-7f25-bc68-171fb66d446e", None, None),
        ("admin", "019adbc3-35e8-7f25-bc68-171fb66d446e", None, None),
        ("owner", "019adbc3-35e8-7f25-bc68-171fb66d446e", None, None),
        ("owner", "019adbc3-35e8-7f25-bc68-171fb66d446e", None, None),
        ("editor", "019adbc3-35e8-7f25-bc68-171fb66d446e", None, None),
        ("editor", "019adbc3-35e8-7f25-bc68-171fb66d446e", None, None),
        (
            "viewer",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            "apikey",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            "anonymous",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            "anonymous",
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "ETL task does not exist",
            404,
        ),
        (
            None,
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            None,
            "019adbc3-35e8-7f25-bc68-171fb66d446e",
            "ETL task does not exist",
            404,
        ),
        (
            None,
            "00000000-0000-0000-0000-000000000000",
            "ETL task does not exist",
            404,
        ),
    ],
)
def test_delete_task(
    get_principal, principal, task, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            task_service.delete(
                principal=get_principal(principal), uid=uuid.UUID(task)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        task_delete = task_service.delete(
            principal=get_principal(principal), uid=uuid.UUID(task)
        )
        assert task_delete == "ETL Task deleted"
