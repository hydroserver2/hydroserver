import uuid

from ninja import Router, Path, Query

from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth
from processing.orchestration.models import TaskRun
from interfaces.api.services.monitoring.task import MonitoringTaskAPIService
from processing.monitoring.tasks import run_monitoring_task
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.monitoring.task import (
    MonitoringTaskQueryParameters,
    MonitoringTaskItemQueryParameters,
    MonitoringTaskResponse,
    MonitoringTaskPostBody,
    MonitoringTaskPatchBody,
)
from interfaces.api.schemas.orchestration.run import TaskRunQueryParameters, TaskRunResponse

monitoring_task_router = Router(tags=["Monitoring Tasks"])
monitoring_task_service = MonitoringTaskAPIService()


@monitoring_task_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: PaginatedResponse[MonitoringTaskResponse],
        401: str,
    },
    by_alias=True,
)
def get_monitoring_tasks(
    request: HydroServerHttpRequest,
    query: Query[MonitoringTaskQueryParameters],
):
    """
    Get monitoring tasks accessible to the authenticated user.
    """

    return 200, monitoring_task_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@monitoring_task_router.post(
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
def create_monitoring_task(
    request: HydroServerHttpRequest,
    data: MonitoringTaskPostBody,
):
    """
    Create a new monitoring task.
    """

    return 201, monitoring_task_service.create(principal=request.principal, data=data)


@monitoring_task_router.get(
    "/{task_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: ItemResponse[MonitoringTaskResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_monitoring_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    query: Query[MonitoringTaskItemQueryParameters],
):
    """
    Get a monitoring task.
    """

    return 200, monitoring_task_service.get_item(
        principal=request.principal, uid=task_id, include=query.include
    )


@monitoring_task_router.patch(
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
def update_monitoring_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    data: MonitoringTaskPatchBody,
):
    """
    Update a monitoring task.
    """

    monitoring_task_service.update(principal=request.principal, uid=task_id, data=data)

    return 204, None


@monitoring_task_router.delete(
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
def delete_monitoring_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Delete a monitoring task.
    """

    monitoring_task_service.delete(
        task=task_id,
        principal=request.principal,
    )

    return 204, None


@monitoring_task_router.post(
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
def trigger_monitoring_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Trigger an immediate run of a monitoring task on a Celery worker.
    """

    task = monitoring_task_service.get_task_for_action(
        principal=request.principal, uid=task_id, action="edit"
    )

    run = TaskRun.objects.create(task=task, status="PENDING")
    run_monitoring_task.apply_async(kwargs={"task_id": str(task.id), "run_id": str(run.id)})

    return 202, run


@monitoring_task_router.get(
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
def get_monitoring_task_runs(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    query: Query[TaskRunQueryParameters],
):
    """
    Get runs for a monitoring task.
    """

    count, runs = monitoring_task_service.get_run_collection(
        task=task_id,
        principal=request.principal,
        sortby=query.sortby,
        **query.model_dump(exclude_unset=True, exclude={"sortby"}),
    )

    meta = monitoring_task_service.build_pagination_meta(
        count=count,
        offset=query.offset,
        limit=query.limit,
    )

    return 200, {"data": runs, "meta": meta}


@monitoring_task_router.get(
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
def get_monitoring_task_run(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    run_id: Path[uuid.UUID],
):
    """
    Get a single run for a monitoring task.
    """

    run = monitoring_task_service.get_run(
        task=task_id,
        run=run_id,
        principal=request.principal,
    )

    return 200, run
