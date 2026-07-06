import uuid
from typing import Optional

from ninja import Router, Path, Query
from django.http import HttpResponse

from core.types import Unset
from interfaces.api.http.errors import raise_http_errors
from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import bearer_auth, session_auth, apikey_auth
from processing.orchestration.models import TaskRun
from processing.etl.services.task import EtlTaskService
from processing.etl.tasks import run_etl_task
from interfaces.api.schemas.etl.task import (
    EtlTaskQueryParameters,
    EtlTaskSummaryResponse,
    EtlTaskDetailResponse,
    EtlTaskPostBody,
    EtlTaskPatchBody,
)
from interfaces.api.schemas.orchestration.run import TaskRunQueryParameters, TaskRunResponse

etl_task_router = Router(tags=["ETL Tasks"])
etl_task_service = EtlTaskService()


@etl_task_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: list[EtlTaskSummaryResponse] | list[EtlTaskDetailResponse],
        401: str,
    },
    by_alias=True,
)
def get_etl_tasks(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[EtlTaskQueryParameters],
):
    """
    Get ETL Tasks accessible to the authenticated user.
    """

    with raise_http_errors():
        count, etl_tasks = etl_task_service.get_collection(
            principal=request.principal,
            order_by=[f.orm_field for f in query.order_by],
            **query.model_dump(exclude_unset=True, exclude={
                "order_by", "thing_id", "workspace_id", "data_connection_id",
                "latest_run_started_at_min", "latest_run_started_at_max",
                "latest_run_finished_at_min", "latest_run_finished_at_max",
            }),
            **({"thing": query.thing_id} if "thing_id" in query.model_fields_set else {}),
            **({"workspace": query.workspace_id} if "workspace_id" in query.model_fields_set else {}),
            **({"data_connection": query.data_connection_id}
               if "data_connection_id" in query.model_fields_set else {}),
            **({"latest_run_started_at_min": query.latest_run_started_at_min}
               if query.latest_run_started_at_min is not None else {}),
            **({"latest_run_started_at_max": query.latest_run_started_at_max}
               if query.latest_run_started_at_max is not None else {}),
            **({"latest_run_finished_at_min": query.latest_run_finished_at_min}
               if query.latest_run_finished_at_min is not None else {}),
            **({"latest_run_finished_at_max": query.latest_run_finished_at_max}
               if query.latest_run_finished_at_max is not None else {}),
        )

    schema = EtlTaskDetailResponse if query.expand_related else EtlTaskSummaryResponse

    apply_response_pagination_headers(
        response=response,
        count=count,
        page=query.page,
        page_size=query.page_size,
    )

    return 200, [schema.model_validate(task) for task in etl_tasks]


@etl_task_router.post(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: EtlTaskSummaryResponse,
        400: str,
        401: str,
        403: str,
        409: str,
        422: str,
    },
    by_alias=True,
)
def create_etl_task(
    request: HydroServerHttpRequest,
    data: EtlTaskPostBody,
):
    """
    Create a new ETL Task.
    """

    with raise_http_errors():
        etl_task = etl_task_service.create(
            principal=request.principal,
            data_connection=data.data_connection_id,
            mappings=[
                {"source_identifier": m.source_identifier, "target_datastream": m.target_datastream_id}
                for m in data.mappings
            ],
            **data.model_dump(exclude_unset=True, exclude={"data_connection_id", "schedule", "mappings"}),
            **(data.schedule.model_dump(exclude_unset=True) if data.schedule else {}),
        )

    return 201, etl_task


@etl_task_router.get(
    "/{task_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: EtlTaskSummaryResponse | EtlTaskDetailResponse,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_etl_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    expand_related: Optional[bool] = None,
):
    """
    Get an ETL Task.
    """

    with raise_http_errors():
        etl_task = etl_task_service.get(
            task=task_id,
            principal=request.principal,
            expand_related=expand_related,
        )

    schema = EtlTaskDetailResponse if expand_related else EtlTaskSummaryResponse
    
    return 200, schema.model_validate(etl_task)


@etl_task_router.patch(
    "/{task_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: EtlTaskSummaryResponse,
        400: str,
        401: str,
        403: str,
        404: str,
        422: str,
    },
    by_alias=True,
)
def update_etl_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    data: EtlTaskPatchBody,
):
    """
    Update an ETL Task.
    """

    with raise_http_errors():
        etl_task = etl_task_service.update(
            task=task_id,
            principal=request.principal,
            mappings=(
                [{"source_identifier": m.source_identifier, "target_datastream": m.target_datastream_id}
                 for m in data.mappings]
                if "mappings" in data.model_fields_set else Unset
            ),
            **data.model_dump(exclude_unset=True, exclude={"schedule", "mappings"}),
            **(
                data.schedule.model_dump(exclude_unset=True)
                if "schedule" in data.model_fields_set and data.schedule
                else {"crontab": None, "interval": None}
                if "schedule" in data.model_fields_set
                else {}
            )
        )

    return 200, etl_task


@etl_task_router.delete(
    "/{task_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        204: None,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def delete_etl_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Delete an ETL Task.
    """

    with raise_http_errors():
        etl_task_service.delete(
            task=task_id,
            principal=request.principal,
        )

    return 204, None


@etl_task_router.post(
    "/{task_id}/trigger",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        202: TaskRunResponse,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def trigger_etl_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Trigger an immediate run of an ETL Task on a Celery worker.
    """

    with raise_http_errors():
        etl_task = etl_task_service.get(
            task=task_id,
            principal=request.principal,
            action="edit"
        )

        run = TaskRun.objects.create(task=etl_task, status="PENDING")
        run_etl_task.apply_async(kwargs={"task_id": str(etl_task.id), "run_id": str(run.id)})

    return 202, run


@etl_task_router.get(
    "/{task_id}/runs",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: list[TaskRunResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_etl_task_runs(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    task_id: Path[uuid.UUID],
    query: Query[TaskRunQueryParameters],
):
    """
    Get runs for an ETL Task.
    """

    with raise_http_errors():
        count, runs = etl_task_service.get_run_collection(
            task=task_id,
            principal=request.principal,
            order_by=[f.orm_field for f in query.order_by],
            **query.model_dump(exclude_unset=True, exclude={"order_by"}),
        )

    apply_response_pagination_headers(
        response=response,
        count=count,
        page=query.page,
        page_size=query.page_size,
    )

    return 200, runs


@etl_task_router.get(
    "/{task_id}/runs/{run_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: TaskRunResponse,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_etl_task_run(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    run_id: Path[uuid.UUID],
):
    """
    Get a single run for an ETL Task.
    """

    with raise_http_errors():
        run = etl_task_service.get_run(
            task=task_id,
            run=run_id,
            principal=request.principal,
        )

    return 200, run
