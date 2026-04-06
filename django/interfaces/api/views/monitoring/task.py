import uuid

from ninja import Router, Path, Query
from django.http import HttpResponse

from interfaces.api.http.errors import raise_http_errors
from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import bearer_auth, session_auth, apikey_auth
from processing.monitoring.services.task import MonitoringTaskService
from processing.monitoring.tasks import run_monitoring_task
from interfaces.api.schemas.monitoring.task import (
    MonitoringTaskResponse,
    MonitoringTaskPostBody,
    MonitoringTaskPatchBody,
    MonitoringTaskQueryParameters,
)
from interfaces.api.schemas.orchestration.run import TaskRunQueryParameters, TaskRunResponse

monitoring_task_router = Router(tags=["Monitoring Tasks"])
monitoring_task_service = MonitoringTaskService()


@monitoring_task_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: list[MonitoringTaskResponse],
        401: str,
    },
    by_alias=True,
)
def get_monitoring_tasks(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[MonitoringTaskQueryParameters],
):
    """
    Get monitoring tasks accessible to the authenticated user.
    """

    with raise_http_errors():
        count, tasks = monitoring_task_service.get_collection(
            principal=request.principal,
            order_by=[f.orm_field for f in query.order_by],
            **query.model_dump(exclude_unset=True, exclude={"order_by", "thing", "workspace", "datastream", "rule_type"}),
            **({"thing": query.thing} if "thing" in query.model_fields_set else {}),
            **({"workspace": query.workspace} if "workspace" in query.model_fields_set else {}),
            **({"datastream": query.datastream} if "datastream" in query.model_fields_set else {}),
            **({"rule_type": query.rule_type} if "rule_type" in query.model_fields_set else {}),
        )

    apply_response_pagination_headers(
        response=response,
        count=count,
        page=query.page,
        page_size=query.page_size,
    )

    return 200, tasks


@monitoring_task_router.post(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: MonitoringTaskResponse,
        400: str,
        401: str,
        403: str,
        404: str,
        422: str,
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

    with raise_http_errors():
        task = monitoring_task_service.create(
            principal=request.principal,
            thing=data.thing_id,
            **data.model_dump(exclude_unset=True, exclude={"thing_id", "schedule"}),
            **(data.schedule.model_dump(exclude_unset=True) if data.schedule else {}),
        )

    return 201, task


@monitoring_task_router.get(
    "/{task_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: MonitoringTaskResponse,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_monitoring_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Get a monitoring task.
    """

    with raise_http_errors():
        task = monitoring_task_service.get(
            task=task_id,
            principal=request.principal,
        )

    return 200, task


@monitoring_task_router.patch(
    "/{task_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: MonitoringTaskResponse,
        400: str,
        401: str,
        403: str,
        404: str,
        422: str,
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

    extra = {}

    if "schedule" in data.model_fields_set:
        extra.update(data.schedule.model_dump(exclude_unset=True) if data.schedule else {})

    with raise_http_errors():
        task = monitoring_task_service.update(
            task=task_id,
            principal=request.principal,
            **data.model_dump(exclude_unset=True, exclude={"schedule"}),
            **extra,
        )

    return 200, task


@monitoring_task_router.delete(
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
def delete_monitoring_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Delete a monitoring task.
    """

    with raise_http_errors():
        monitoring_task_service.delete(
            task=task_id,
            principal=request.principal,
        )

    return 204, None


@monitoring_task_router.post(
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
def trigger_monitoring_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Trigger an immediate run of a monitoring task on a Celery worker.
    """

    from processing.orchestration.models import TaskRun

    with raise_http_errors():
        task = monitoring_task_service.get(
            task=task_id,
            principal=request.principal,
            action="edit",
        )

        run = TaskRun.objects.create(task=task, status="PENDING")
        run_monitoring_task.apply_async(kwargs={"task_id": str(task.id), "run_id": str(run.id)})

    return 202, run


@monitoring_task_router.get(
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
def get_monitoring_task_runs(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    task_id: Path[uuid.UUID],
    query: Query[TaskRunQueryParameters],
):
    """
    Get runs for a monitoring task.
    """

    with raise_http_errors():
        count, runs = monitoring_task_service.get_run_collection(
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


@monitoring_task_router.get(
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
def get_monitoring_task_run(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    run_id: Path[uuid.UUID],
):
    """
    Get a single run for a monitoring task.
    """

    with raise_http_errors():
        run = monitoring_task_service.get_run(
            task=task_id,
            run=run_id,
            principal=request.principal,
        )

    return 200, run