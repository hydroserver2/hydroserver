# import pytest
# import uuid
# from collections import Counter
# from ninja.errors import HttpError
# from django.http import HttpResponse
# from processing.etl.services import EtlTaskService
# from processing.etl.schemas import (
#     EtlTaskSummaryResponse,
#     EtlTaskDetailResponse,
#     EtlTaskPostBody,
#     EtlTaskPatchBody,
#     EtlMappingPostBody,
# )
# from processing.orchestration.schemas import SchedulePostBody, TaskRunResponse
# from processing.etl.tasks import run_etl_task
#
# etl_task_service = EtlTaskService()
#
# ETL_TASK_PK = "019adbc3-35e8-7f25-bc68-171fb66d446e"
# DC1_PK = "019adb5c-da8b-7970-877d-c3b4ca37cc60"
# DC2_PK = "019bbd9d-ee62-7669-8db0-3ef50802f1d8"
# PRIVATE_WORKSPACE = "b27c51a0-7374-462d-8a53-d97d47176c10"
# PUBLIC_WORKSPACE = "6e0deaf2-a92b-421b-9ece-86783265596f"
# DATASTREAM_PK = "27c70b41-e845-40ea-8cc7-d1b40f89816b"
#
#
# @pytest.mark.parametrize(
#     "principal, params, task_names, max_queries",
#     [
#         # Test user access
#         ("owner", {}, ["Test ETL Task"], 10),
#         ("editor", {}, ["Test ETL Task"], 10),
#         ("viewer", {}, ["Test ETL Task"], 10),
#         ("admin", {}, ["Test ETL Task"], 10),
#         ("apikey", {}, [], 6),
#         ("unaffiliated", {}, [], 6),
#         ("anonymous", {}, [], 4),
#         # Test pagination and order_by
#         ("owner", {"page": 2, "page_size": 1, "order_by": "-name"}, [], 10),
#         # Test workspace filtering
#         (
#             "owner",
#             {"workspace_id": [PRIVATE_WORKSPACE]},
#             ["Test ETL Task"],
#             10,
#         ),
#     ],
# )
# def test_list_etl_task(
#     django_assert_max_num_queries,
#     get_principal,
#     principal,
#     params,
#     task_names,
#     max_queries,
# ):
#     with django_assert_max_num_queries(max_queries):
#         http_response = HttpResponse()
#         result = etl_task_service.list(
#             principal=get_principal(principal),
#             response=http_response,
#             page=params.pop("page", 1),
#             page_size=params.pop("page_size", 100),
#             order_by=[params.pop("order_by")] if "order_by" in params else [],
#             filtering=params,
#         )
#         assert Counter(task.name for task in result) == Counter(task_names)
#         assert all(isinstance(task, EtlTaskSummaryResponse) for task in result)
#
#
# @pytest.mark.parametrize(
#     "principal, task_id, expected_name, error_code",
#     [
#         ("owner", ETL_TASK_PK, "Test ETL Task", None),
#         ("admin", ETL_TASK_PK, "Test ETL Task", None),
#         ("editor", ETL_TASK_PK, "Test ETL Task", None),
#         ("viewer", ETL_TASK_PK, "Test ETL Task", None),
#         ("apikey", ETL_TASK_PK, "ETL task does not exist", 404),
#         ("anonymous", ETL_TASK_PK, "ETL task does not exist", 404),
#         ("anonymous", "00000000-0000-0000-0000-000000000000", "ETL task does not exist", 404),
#         (None, ETL_TASK_PK, "ETL task does not exist", 404),
#         (None, "00000000-0000-0000-0000-000000000000", "ETL task does not exist", 404),
#     ],
# )
# def test_get_etl_task(get_principal, principal, task_id, expected_name, error_code):
#     if error_code:
#         with pytest.raises(HttpError) as exc_info:
#             etl_task_service.get(
#                 principal=get_principal(principal), uid=uuid.UUID(task_id)
#             )
#         assert exc_info.value.status_code == error_code
#         assert exc_info.value.message.startswith(expected_name)
#     else:
#         result = etl_task_service.get(
#             principal=get_principal(principal), uid=uuid.UUID(task_id)
#         )
#         assert result.name == expected_name
#         assert isinstance(result, EtlTaskDetailResponse)
#         assert result.schedule is not None
#         assert result.schedule.paused is True
#
#
# def test_get_etl_task_includes_latest_run(get_principal):
#     result = etl_task_service.get(
#         principal=get_principal("owner"), uid=uuid.UUID(ETL_TASK_PK)
#     )
#     assert result.latest_run is not None
#     assert result.latest_run.status == "SUCCESS"
#     assert len(result.mappings) == 1
#     assert result.mappings[0].source_identifier == "test_value"
#
#
# @pytest.mark.parametrize(
#     "principal, workspace, data_connection, message, error_code",
#     [
#         ("admin", PRIVATE_WORKSPACE, DC1_PK, None, None),
#         (
#             "admin",
#             PRIVATE_WORKSPACE,
#             "00000000-0000-0000-0000-000000000000",
#             "Data Connection does not exist",
#             400,
#         ),
#         (
#             "admin",
#             PUBLIC_WORKSPACE,
#             DC1_PK,
#             "Task workspace must match data connection workspace.",
#             400,
#         ),
#         ("owner", PRIVATE_WORKSPACE, DC1_PK, None, None),
#         ("editor", PRIVATE_WORKSPACE, DC1_PK, None, None),
#         (
#             "viewer",
#             PRIVATE_WORKSPACE,
#             DC1_PK,
#             "You do not have permission",
#             400,
#         ),
#         (
#             "anonymous",
#             PRIVATE_WORKSPACE,
#             DC1_PK,
#             "Data Connection does not exist",
#             400,
#         ),
#         (
#             None,
#             PRIVATE_WORKSPACE,
#             DC1_PK,
#             "Data Connection does not exist",
#             400,
#         ),
#     ],
# )
# def test_create_etl_task(
#     get_principal, principal, workspace, data_connection, message, error_code
# ):
#     data = EtlTaskPostBody(
#         name="New ETL Task",
#         workspace_id=uuid.UUID(workspace),
#         data_connection_id=uuid.UUID(data_connection),
#         schedule=SchedulePostBody(paused=True, crontab="* * * * *"),
#         mappings=[
#             EtlMappingPostBody(
#                 source_identifier="col1",
#                 target_datastream_id=uuid.UUID(DATASTREAM_PK),
#             )
#         ],
#     )
#     if error_code:
#         with pytest.raises(HttpError) as exc_info:
#             etl_task_service.create(principal=get_principal(principal), data=data)
#         assert exc_info.value.status_code == error_code
#         assert exc_info.value.message.startswith(message)
#     else:
#         result = etl_task_service.create(principal=get_principal(principal), data=data)
#         assert result.name == data.name
#         assert isinstance(result, EtlTaskDetailResponse)
#         assert result.schedule is not None
#         assert result.schedule.paused is True
#         assert len(result.mappings) == 1
#
#
# @pytest.mark.parametrize(
#     "principal, task_id, message, error_code",
#     [
#         ("admin", ETL_TASK_PK, None, None),
#         ("owner", ETL_TASK_PK, None, None),
#         ("editor", ETL_TASK_PK, None, None),
#         ("viewer", ETL_TASK_PK, "You do not have permission", 403),
#         ("apikey", ETL_TASK_PK, "ETL task does not exist", 404),
#         ("anonymous", ETL_TASK_PK, "ETL task does not exist", 404),
#         ("anonymous", "00000000-0000-0000-0000-000000000000", "ETL task does not exist", 404),
#         (None, ETL_TASK_PK, "ETL task does not exist", 404),
#         (None, "00000000-0000-0000-0000-000000000000", "ETL task does not exist", 404),
#     ],
# )
# def test_edit_etl_task(get_principal, principal, task_id, message, error_code):
#     data = EtlTaskPatchBody(name="Updated Name")
#     if error_code:
#         with pytest.raises(HttpError) as exc_info:
#             etl_task_service.update(
#                 principal=get_principal(principal),
#                 uid=uuid.UUID(task_id),
#                 data=data,
#             )
#         assert exc_info.value.status_code == error_code
#         assert exc_info.value.message.startswith(message)
#     else:
#         result = etl_task_service.update(
#             principal=get_principal(principal),
#             uid=uuid.UUID(task_id),
#             data=data,
#         )
#         assert result.name == data.name
#         assert isinstance(result, EtlTaskDetailResponse)
#
#
# def test_run_etl_task_creates_started_run(get_principal, monkeypatch, settings):
#     settings.CELERY_ENABLED = False
#
#     def fake_apply(*args, **kwargs):
#         pass
#
#     monkeypatch.setattr(run_etl_task, "apply", fake_apply)
#
#     result = etl_task_service.run(
#         principal=get_principal("owner"), uid=uuid.UUID(ETL_TASK_PK)
#     )
#
#     assert isinstance(result, TaskRunResponse)
#     assert result.status == "STARTED"
#     assert result.id is not None
#
#
# @pytest.mark.parametrize(
#     "principal, task_id, message, error_code",
#     [
#         ("viewer", ETL_TASK_PK, "You do not have permission", 403),
#         ("apikey", ETL_TASK_PK, "ETL task does not exist", 404),
#         ("anonymous", ETL_TASK_PK, "ETL task does not exist", 404),
#         (None, ETL_TASK_PK, "ETL task does not exist", 404),
#     ],
# )
# def test_run_etl_task_denied(get_principal, principal, task_id, message, error_code):
#     with pytest.raises(HttpError) as exc_info:
#         etl_task_service.run(
#             principal=get_principal(principal), uid=uuid.UUID(task_id)
#         )
#     assert exc_info.value.status_code == error_code
#     assert exc_info.value.message.startswith(message)
#
#
# @pytest.mark.parametrize(
#     "principal, task_id, message, error_code",
#     [
#         ("admin", ETL_TASK_PK, None, None),
#         ("owner", ETL_TASK_PK, None, None),
#         ("editor", ETL_TASK_PK, None, None),
#         ("viewer", ETL_TASK_PK, "You do not have permission", 403),
#         ("apikey", ETL_TASK_PK, "ETL task does not exist", 404),
#         ("anonymous", ETL_TASK_PK, "ETL task does not exist", 404),
#         ("anonymous", "00000000-0000-0000-0000-000000000000", "ETL task does not exist", 404),
#         (None, ETL_TASK_PK, "ETL task does not exist", 404),
#         (None, "00000000-0000-0000-0000-000000000000", "ETL task does not exist", 404),
#     ],
# )
# def test_delete_etl_task(get_principal, principal, task_id, message, error_code):
#     if error_code:
#         with pytest.raises(HttpError) as exc_info:
#             etl_task_service.delete(
#                 principal=get_principal(principal), uid=uuid.UUID(task_id)
#             )
#         assert exc_info.value.status_code == error_code
#         assert exc_info.value.message.startswith(message)
#     else:
#         result = etl_task_service.delete(
#             principal=get_principal(principal), uid=uuid.UUID(task_id)
#         )
#         assert result == "ETL task deleted"
