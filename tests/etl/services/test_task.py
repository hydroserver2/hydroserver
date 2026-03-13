import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from django.utils import timezone
from domains.etl.models import Task, TaskRun
from domains.etl.services import TaskService
from domains.etl.tasks import run_etl_task
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
            {"task_type": "ETL"},
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


def test_list_task_can_skip_heavy_fields(get_principal):
    http_response = HttpResponse()
    result = task_service.list(
        principal=get_principal("owner"),
        response=http_response,
        page=1,
        page_size=100,
        order_by=[],
        filtering={},
        expand_related=True,
        include_mappings=False,
        include_latest_run_result=False,
        include_data_connection_settings=False,
    )

    assert result
    task = result[0]
    assert task["mappings"] == []
    assert task["latest_run"]["message"] == "OK"
    assert task["latest_run"]["failure_count"] is None
    assert task["latest_run"]["result"] is None
    assert task["target_identifiers"] == ["27c70b41-e845-40ea-8cc7-d1b40f89816b"]
    assert task["data_connection"]["extractor"] is None
    assert task["data_connection"]["transformer"] is None
    assert task["data_connection"]["loader"] is None


def test_list_task_can_expose_failure_count_without_latest_run_result(get_principal):
    task = Task.objects.get(pk="019adbc3-35e8-7f25-bc68-171fb66d446e")
    TaskRun.objects.create(
        task=task,
        status="SUCCESS",
        result={
            "message": "Loaded with issues",
            "failure_count": 2,
        },
    )

    http_response = HttpResponse()
    result = task_service.list(
        principal=get_principal("owner"),
        response=http_response,
        page=1,
        page_size=100,
        order_by=[],
        filtering={},
        expand_related=True,
        include_mappings=False,
        include_latest_run_result=False,
        include_data_connection_settings=False,
    )

    assert result
    lean_task = next(
        task for task in result
        if task["id"] == uuid.UUID("019adbc3-35e8-7f25-bc68-171fb66d446e")
    )
    assert lean_task["latest_run"]["message"] == "Loaded with issues"
    assert lean_task["latest_run"]["failure_count"] == 2
    assert lean_task["latest_run"]["result"] is None


def test_run_task_returns_a_new_running_run(get_principal, monkeypatch, settings):
    settings.CELERY_ENABLED = True
    principal = get_principal("owner")
    task_id = uuid.UUID("019adbc3-35e8-7f25-bc68-171fb66d446e")
    previous_run = TaskRun.objects.filter(task_id=task_id).order_by("-started_at").first()

    recorded: dict[str, str] = {}

    def fake_apply_async(*args, **kwargs):
        recorded["task_id"] = kwargs["task_id"]

    monkeypatch.setattr(run_etl_task, "apply_async", fake_apply_async)

    result = task_service.run(principal=principal, task_id=task_id)

    assert result["status"] == "RUNNING"
    assert result["message"] is None
    assert result["failure_count"] is None
    assert result["id"] is not None
    assert str(result["id"]) != str(previous_run.id)
    assert recorded["task_id"] == str(result["id"])

    created_run = TaskRun.objects.get(id=result["id"])
    assert created_run.task_id == task_id
    assert created_run.status == "RUNNING"


def test_run_task_returns_completed_run_state_in_eager_mode(get_principal, monkeypatch, settings):
    settings.CELERY_ENABLED = False
    principal = get_principal("owner")
    task_id = uuid.UUID("019adbc3-35e8-7f25-bc68-171fb66d446e")

    def fake_apply(*args, **kwargs):
        task_run = TaskRun.objects.get(id=kwargs["task_id"])
        task_run.status = "SUCCESS"
        task_run.finished_at = timezone.now()
        task_run.result = {"message": "Run completed."}
        task_run.save(update_fields=["status", "finished_at", "result"])

    monkeypatch.setattr(run_etl_task, "apply", fake_apply)

    result = task_service.run(principal=principal, task_id=task_id)

    assert result["status"] == "SUCCESS"
    assert result["message"] == "Run completed."
    assert result["result"] == {"message": "Run completed."}
    assert result["finished_at"] is not None


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


def test_create_aggregation_task_without_data_connection(get_principal):
    task_data = TaskPostBody(
        name="New Aggregation Task",
        task_type="Aggregation",
        workspace_id=uuid.UUID("b27c51a0-7374-462d-8a53-d97d47176c10"),
        data_connection_id=None,
        orchestration_system_id=uuid.UUID("019aead4-df4e-7a08-a609-dbc96df6befe"),
        schedule=TaskSchedulePostBody(
            paused=True,
            crontab="* * * * *",
        ),
        mappings=[
            TaskMappingPostBody(
                source_identifier="dd1f9293-ce29-4b6a-88e6-d65110d1be65",
                paths=[
                    TaskMappingPathPostBody(
                        target_identifier="1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
                        data_transformations=[
                            {
                                "type": "aggregation",
                                "aggregationStatistic": "simple_mean",
                                "timezoneMode": "fixedOffset",
                                "timezone": "-0700",
                            }
                        ],
                    )
                ],
            )
        ],
    )

    task_create = task_service.create(
        principal=get_principal("owner"),
        data=task_data,
    )
    assert task_create["task_type"] == "Aggregation"
    assert task_create["data_connection"] is None
    assert TaskDetailResponse.from_orm(task_create)


def test_create_etl_task_requires_data_connection(get_principal):
    task_data = TaskPostBody(
        name="New ETL Task Without Data Connection",
        task_type="ETL",
        workspace_id=uuid.UUID("b27c51a0-7374-462d-8a53-d97d47176c10"),
        data_connection_id=None,
        orchestration_system_id=uuid.UUID("019aead4-df4e-7a08-a609-dbc96df6befe"),
        schedule=TaskSchedulePostBody(
            paused=True,
            crontab="* * * * *",
        ),
        mappings=[
            TaskMappingPostBody(
                source_identifier="test",
                paths=[TaskMappingPathPostBody(target_identifier="test")],
            )
        ],
    )

    with pytest.raises(HttpError) as exc_info:
        task_service.create(
            principal=get_principal("owner"),
            data=task_data,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.message == "ETL tasks require a data connection."


def test_create_aggregation_task_supports_multiple_source_target_mappings(get_principal):
    aggregation_transform = {
        "type": "aggregation",
        "aggregationStatistic": "simple_mean",
        "timezoneMode": "fixedOffset",
        "timezone": "-0700",
    }

    task_data = TaskPostBody(
        name="Aggregation Task With Multiple Mappings",
        task_type="Aggregation",
        workspace_id=uuid.UUID("b27c51a0-7374-462d-8a53-d97d47176c10"),
        data_connection_id=None,
        orchestration_system_id=uuid.UUID("019aead4-df4e-7a08-a609-dbc96df6befe"),
        schedule=TaskSchedulePostBody(
            paused=True,
            crontab="* * * * *",
        ),
        mappings=[
            TaskMappingPostBody(
                source_identifier="dd1f9293-ce29-4b6a-88e6-d65110d1be65",
                paths=[
                    TaskMappingPathPostBody(
                        target_identifier="1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
                        data_transformations=[aggregation_transform],
                    )
                ],
            ),
            TaskMappingPostBody(
                source_identifier="42e08eea-27bb-4ea3-8ced-63acff0f3334",
                paths=[
                    TaskMappingPathPostBody(
                        target_identifier="9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
                        data_transformations=[aggregation_transform],
                    )
                ],
            ),
        ],
    )

    task_create = task_service.create(
        principal=get_principal("owner"),
        data=task_data,
    )
    assert task_create["task_type"] == "Aggregation"
    assert len(task_create["mappings"]) == 2
    assert TaskDetailResponse.from_orm(task_create)


def test_create_aggregation_task_rejects_multiple_paths_per_mapping(get_principal):
    aggregation_transform = {
        "type": "aggregation",
        "aggregationStatistic": "simple_mean",
        "timezoneMode": "fixedOffset",
        "timezone": "-0700",
    }

    task_data = TaskPostBody(
        name="Aggregation Task With Branched Mapping",
        task_type="Aggregation",
        workspace_id=uuid.UUID("b27c51a0-7374-462d-8a53-d97d47176c10"),
        data_connection_id=None,
        orchestration_system_id=uuid.UUID("019aead4-df4e-7a08-a609-dbc96df6befe"),
        schedule=TaskSchedulePostBody(
            paused=True,
            crontab="* * * * *",
        ),
        mappings=[
            TaskMappingPostBody(
                source_identifier="dd1f9293-ce29-4b6a-88e6-d65110d1be65",
                paths=[
                    TaskMappingPathPostBody(
                        target_identifier="1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
                        data_transformations=[aggregation_transform],
                    ),
                    TaskMappingPathPostBody(
                        target_identifier="9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
                        data_transformations=[aggregation_transform],
                    ),
                ],
            ),
        ],
    )

    with pytest.raises(HttpError) as exc_info:
        task_service.create(
            principal=get_principal("owner"),
            data=task_data,
        )
    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.message
        == "Aggregation mappings currently support exactly one target path per source."
    )


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
