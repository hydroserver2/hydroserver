import uuid

from ninja import Router, Path, Query

from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth
from processing.orchestration.models import TaskRun
from interfaces.api.services.etl.task import EtlTaskAPIService
from processing.etl.tasks import run_etl_task
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.etl.task import (
    EtlTaskQueryParameters,
    EtlTaskItemQueryParameters,
    EtlTaskResponse,
    EtlTaskPostBody,
    EtlTaskPatchBody,
)
from interfaces.api.schemas.orchestration.run import TaskRunQueryParameters, TaskRunResponse

etl_task_router = Router(tags=["ETL Tasks"])
etl_task_service = EtlTaskAPIService()


@etl_task_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: PaginatedResponse[EtlTaskResponse],
        401: str,
    },
    by_alias=True,
)
def get_etl_tasks(
    request: HydroServerHttpRequest,
    query: Query[EtlTaskQueryParameters],
):
    """
    Get ETL Tasks accessible to the authenticated user.
    """

    return 200, etl_task_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
        properties=query.properties,
    )


@etl_task_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: CreatedResponse,
        400: str,
        401: str,
        403: str,
        409: str,
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

    return 201, etl_task_service.create(principal=request.principal, data=data)


@etl_task_router.get(
    "/{task_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: ItemResponse[EtlTaskResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_etl_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    query: Query[EtlTaskItemQueryParameters],
):
    """
    Get an ETL Task.
    """

    return 200, etl_task_service.get_item(
        principal=request.principal, uid=task_id, include=query.include
    )


@etl_task_router.patch(
    "/{task_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        400: str,
        401: str,
        403: str,
        404: str,
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

    etl_task_service.update(principal=request.principal, uid=task_id, data=data)

    return 204, None


@etl_task_router.delete(
    "/{task_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
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

    etl_task_service.delete(
        task=task_id,
        principal=request.principal,
    )

    return 204, None


@etl_task_router.post(
    "/{task_id}/trigger",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
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

    etl_task = etl_task_service.get_task_for_action(
        principal=request.principal, uid=task_id, action="edit"
    )

    run = TaskRun.objects.create(task=etl_task, status="PENDING")
    run_etl_task.apply_async(kwargs={"task_id": str(etl_task.id), "run_id": str(run.id)})

    return 202, run


@etl_task_router.get(
    "/{task_id}/runs",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: PaginatedResponse[TaskRunResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_etl_task_runs(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    query: Query[TaskRunQueryParameters],
):
    """
    Get runs for an ETL Task.
    """

    run_kwargs = query.model_dump(
        exclude_unset=True,
        include={
            "offset", "limit", "order_by", "status",
            "started_at__gte", "started_at__lte", "finished_at__gte", "finished_at__lte",
        },
    )
    count, runs = etl_task_service.get_run_collection(
        task=task_id,
        principal=request.principal,
        **run_kwargs,
    )

    meta = etl_task_service.build_pagination_meta(
        count=count,
        offset=query.offset,
        limit=query.limit,
    )

    return 200, {"data": runs, "meta": meta}


@etl_task_router.get(
    "/{task_id}/runs/{run_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
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

    run = etl_task_service.get_run(
        task=task_id,
        run=run_id,
        principal=request.principal,
    )

    return 200, run
