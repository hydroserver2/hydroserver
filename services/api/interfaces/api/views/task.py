import uuid
from ninja import Router, Path, Query
from django.http import HttpResponse
from django.db import transaction
from interfaces.http.request import HydroServerHttpRequest
from interfaces.http.auth import bearer_auth, session_auth, apikey_auth
from domains.etl.services import TaskService
from interfaces.api.schemas import (TaskSummaryResponse, TaskDetailResponse, TaskPostBody, TaskPatchBody, TaskQueryParameters,
                                    TaskRunResponse)


task_router = Router(tags=["ETL Tasks"])
task_service = TaskService()


@task_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: list[TaskSummaryResponse] | list[TaskDetailResponse],
        401: str,
    },
    by_alias=True,
)
def get_tasks(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[TaskQueryParameters],
):
    """
    Get ETL Tasks associated with the authenticated user.
    """

    return 200, task_service.list(
        principal=request.principal,
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        expand_related=query.expand_related,
    )


@task_router.post(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: TaskDetailResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def create_task(
    request: HydroServerHttpRequest,
    data: TaskPostBody
):
    """
    Create a new ETL Task.
    """

    return 201, task_service.create(
        principal=request.principal, data=data
    )


@task_router.get(
    "/{task_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: TaskSummaryResponse | TaskDetailResponse,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    expand_related: bool | None = None,
):
    """
    Get an ETL Task.
    """

    return 200, task_service.get(
        principal=request.principal, uid=task_id, expand_related=expand_related,
    )


@task_router.post(
    "/{task_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: TaskRunResponse,
        202: TaskRunResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
def run_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Run an ETL Task.
    """

    return 200, task_service.run(
        principal=request.principal, task_id=task_id
    )


@task_router.patch(
    "/{task_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: TaskDetailResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    data: TaskPatchBody,
):
    """
    Update an ETL Task.
    """

    return 200, task_service.update(
        principal=request.principal,
        uid=task_id,
        data=data,
    )


@task_router.delete(
    "/{task_id}",
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
def delete_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Delete an ETL Task.
    """

    return 204, task_service.delete(
        principal=request.principal, uid=task_id
    )
