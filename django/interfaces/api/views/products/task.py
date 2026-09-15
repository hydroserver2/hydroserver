import uuid

from ninja import Router, Path, Query

from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth
from processing.orchestration.models import TaskRun
from interfaces.api.services.products.task import DataProductTaskAPIService
from processing.products.tasks import run_data_product_task
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.products.task import (
    DataProductTaskResponse,
    DataProductTaskPostBody,
    DataProductTaskPatchBody,
    DataProductTaskQueryParameters,
    DataProductTaskItemQueryParameters,
)
from interfaces.api.schemas.orchestration.run import TaskRunQueryParameters, TaskRunResponse

data_product_task_router = Router(tags=["Data Product Tasks"])
data_product_task_service = DataProductTaskAPIService()


@data_product_task_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: PaginatedResponse[DataProductTaskResponse],
        401: str,
    },
    by_alias=True,
)
def get_data_product_tasks(
    request: HydroServerHttpRequest,
    query: Query[DataProductTaskQueryParameters],
):
    """
    Get data product tasks accessible to the authenticated user.
    """

    return 200, data_product_task_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@data_product_task_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: CreatedResponse,
        400: str,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def create_data_product_task(
    request: HydroServerHttpRequest,
    data: DataProductTaskPostBody,
):
    """
    Create a new data product task.
    """

    return 201, data_product_task_service.create(principal=request.principal, data=data)


@data_product_task_router.get(
    "/{task_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: ItemResponse[DataProductTaskResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_data_product_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    query: Query[DataProductTaskItemQueryParameters],
):
    """
    Get a data product task.
    """

    return 200, data_product_task_service.get_item(
        principal=request.principal, uid=task_id, include=query.include
    )


@data_product_task_router.patch(
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
def update_data_product_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    data: DataProductTaskPatchBody,
):
    """
    Update a data product task.
    """

    data_product_task_service.update(
        principal=request.principal, uid=task_id, data=data
    )

    return 204, None


@data_product_task_router.delete(
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
def delete_data_product_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Delete a data product task.
    """

    data_product_task_service.delete(
        task=task_id,
        principal=request.principal,
    )

    return 204, None


@data_product_task_router.post(
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
def trigger_data_product_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Trigger an immediate run of a data product task on a Celery worker.
    """

    task = data_product_task_service.get_task_for_action(
        principal=request.principal, uid=task_id, action="edit"
    )

    run = TaskRun.objects.create(task=task, status="PENDING")
    run_data_product_task.apply_async(kwargs={"task_id": str(task.id), "run_id": str(run.id)})

    return 202, run


@data_product_task_router.get(
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
def get_data_product_task_runs(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    query: Query[TaskRunQueryParameters],
):
    """
    Get runs for a data product task.
    """

    count, runs = data_product_task_service.get_run_collection(
        task=task_id,
        principal=request.principal,
        sortby=query.sortby,
        **query.model_dump(exclude_unset=True, exclude={"sortby"}),
    )

    meta = data_product_task_service.build_pagination_meta(
        count=count,
        offset=query.offset,
        limit=query.limit,
    )

    return 200, {"data": runs, "meta": meta}


@data_product_task_router.get(
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
def get_data_product_task_run(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    run_id: Path[uuid.UUID],
):
    """
    Get a single run for a data product task.
    """

    run = data_product_task_service.get_run(
        task=task_id,
        run=run_id,
        principal=request.principal,
    )

    return 200, run
