import uuid

from ninja import Router, Path, Query
from django.http import HttpResponse

from core.types import Unset
from interfaces.api.http.errors import raise_http_errors
from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import bearer_auth, session_auth, apikey_auth
from processing.orchestration.models import TaskRun
from processing.products.services.task import DataProductTaskService
from processing.products.tasks import run_data_product_task
from interfaces.api.schemas.products.task import (
    DataProductTaskResponse,
    DataProductTaskPostBody,
    DataProductTaskPatchBody,
    DataProductTaskQueryParameters,
)
from interfaces.api.schemas.orchestration.run import TaskRunQueryParameters, TaskRunResponse

data_product_task_router = Router(tags=["Data Product Tasks"])
data_product_task_service = DataProductTaskService()


@data_product_task_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: list[DataProductTaskResponse],
        401: str,
    },
    by_alias=True,
)
def get_data_product_tasks(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[DataProductTaskQueryParameters],
):
    """
    Get data product tasks accessible to the authenticated user.
    """

    with raise_http_errors():
        count, tasks = data_product_task_service.get_collection(
            principal=request.principal,
            order_by=[f.orm_field for f in query.order_by],
            **query.model_dump(exclude_unset=True, exclude={
                "order_by", "thing", "workspace",
                "output_datastream", "input_datastream", "rating_curve",
            }),
            **({"thing": query.thing} if "thing" in query.model_fields_set else {}),
            **({"workspace": query.workspace} if "workspace" in query.model_fields_set else {}),
            **({"output_datastream": query.output_datastream} if "output_datastream" in query.model_fields_set else {}),
            **({"input_datastream": query.input_datastream} if "input_datastream" in query.model_fields_set else {}),
            **({"rating_curve": query.rating_curve} if "rating_curve" in query.model_fields_set else {}),
        )

    apply_response_pagination_headers(
        response=response,
        count=count,
        page=query.page,
        page_size=query.page_size,
    )

    return 200, tasks


@data_product_task_router.post(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: DataProductTaskResponse,
        400: str,
        401: str,
        403: str,
        404: str,
        422: str,
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

    with raise_http_errors():
        task = data_product_task_service.create(
            principal=request.principal,
            thing=data.thing_id,
            **data.model_dump(exclude_unset=True, exclude={"thing_id", "uid", "schedule"}),
            **({"uid": data.uid} if data.uid is not Unset else {}),
            **(data.schedule.model_dump(exclude_unset=True) if data.schedule else {}),
        )

    return 201, task


@data_product_task_router.get(
    "/{task_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: DataProductTaskResponse,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_data_product_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Get a data product task.
    """

    with raise_http_errors():
        task = data_product_task_service.get(
            task=task_id,
            principal=request.principal,
        )

    return 200, task


@data_product_task_router.patch(
    "/{task_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: DataProductTaskResponse,
        400: str,
        401: str,
        403: str,
        404: str,
        422: str,
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

    with raise_http_errors():
        task = data_product_task_service.update(
            task=task_id,
            principal=request.principal,
            **data.model_dump(exclude_unset=True, exclude={"schedule"}),
            **(
                data.schedule.model_dump(exclude_unset=True)
                if "schedule" in data.model_fields_set and data.schedule
                else {"crontab": None, "interval": None}
                if "schedule" in data.model_fields_set
                else {}
            ),
        )

    return 200, task


@data_product_task_router.delete(
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
def delete_data_product_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Delete a data product task.
    """

    with raise_http_errors():
        data_product_task_service.delete(
            task=task_id,
            principal=request.principal,
        )

    return 204, None


@data_product_task_router.post(
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
def trigger_data_product_task(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
):
    """
    Trigger an immediate run of a data product task on a Celery worker.
    """

    with raise_http_errors():
        task = data_product_task_service.get(
            task=task_id,
            principal=request.principal,
            action="edit",
        )

        run = TaskRun.objects.create(task=task, status="PENDING")
        run_data_product_task.apply_async(kwargs={"task_id": str(task.id), "run_id": str(run.id)})

    return 202, run


@data_product_task_router.get(
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
def get_data_product_task_runs(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    task_id: Path[uuid.UUID],
    query: Query[TaskRunQueryParameters],
):
    """
    Get runs for a data product task.
    """

    with raise_http_errors():
        count, runs = data_product_task_service.get_run_collection(
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


@data_product_task_router.get(
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
def get_data_product_task_run(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    run_id: Path[uuid.UUID],
):
    """
    Get a single run for a data product task.
    """

    with raise_http_errors():
        run = data_product_task_service.get_run(
            task=task_id,
            run=run_id,
            principal=request.principal,
        )

    return 200, run
