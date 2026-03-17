import uuid
from ninja import Router, Path, Query
from django.http import HttpResponse
from django.db import transaction
from interfaces.http.request import HydroServerHttpRequest
from interfaces.http.auth import bearer_auth, session_auth, apikey_auth
from domains.etl.services import TaskRunService
from interfaces.api.schemas import TaskRunResponse, TaskRunPostBody, TaskRunPatchBody, TaskRunQueryParameters


task_run_router = Router(tags=["ETL Task Runs"])
task_run_service = TaskRunService()


@task_run_router.get(
    "/{task_id}/runs",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: list[TaskRunResponse],
        401: str,
    },
    by_alias=True,
)
def get_task_runs(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    task_id: Path[uuid.UUID],
    query: Query[TaskRunQueryParameters],
):
    """
    Get all runs for an ETL Task.
    """

    return 200, task_run_service.list(
        principal=request.principal,
        response=response,
        task_id=task_id,
        page=query.page,
        page_size=query.page_size,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
    )


@task_run_router.post(
    "/{task_id}/runs",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: TaskRunResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
def create_task_run(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    data: TaskRunPostBody
):
    """
    Create a new ETL Task run.
    """

    return 201, task_run_service.create(
        principal=request.principal, task_id=task_id, data=data
    )


@task_run_router.get(
    "/{task_id}/runs/{run_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: TaskRunResponse,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_task_run(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    run_id: Path[uuid.UUID],
):
    """
    Get an ETL Task Run.
    """

    return 200, task_run_service.get(
        principal=request.principal, uid=run_id, task_id=task_id,
    )


@task_run_router.patch(
    "/{task_id}/runs/{run_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: TaskRunResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_task_run(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    run_id: Path[uuid.UUID],
    data: TaskRunPatchBody,
):
    """
    Update an ETL Task run.
    """

    return 200, task_run_service.update(
        principal=request.principal,
        uid=run_id,
        task_id=task_id,
        data=data,
    )


@task_run_router.delete(
    "/{task_id}/runs/{run_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        204: None,
        401: str,
        403: str,
        409: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_task_run(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    run_id: Path[uuid.UUID],
):
    """
    Delete an ETL Task run.
    """

    return 204, task_run_service.delete(
        principal=request.principal, uid=run_id, task_id=task_id
    )
