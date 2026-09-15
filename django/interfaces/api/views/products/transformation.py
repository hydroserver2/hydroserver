import uuid

from ninja import Router, Path, Query

from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth
from interfaces.api.services.products.transformation import DataProductTransformationAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.products.transformation import (
    DataProductTransformationResponse,
    DataProductTransformationPostBody,
    DataProductTransformationPatchBody,
    DataProductTransformationQueryParameters,
    DataProductTransformationItemQueryParameters,
)

data_product_transformation_router = Router(tags=["Transformations"])
_service = DataProductTransformationAPIService()


@data_product_transformation_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: PaginatedResponse[DataProductTransformationResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_data_product_transformations(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    query: Query[DataProductTransformationQueryParameters],
):
    """Get transformations for a data product task."""

    return 200, _service.list(
        principal=request.principal,
        task_id=task_id,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@data_product_transformation_router.post(
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
def create_data_product_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    data: DataProductTransformationPostBody,
):
    """Create a transformation on a data product task."""

    return 201, _service.create(
        principal=request.principal,
        task_id=task_id,
        data=data,
    )


@data_product_transformation_router.get(
    "/{transformation_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: ItemResponse[DataProductTransformationResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_data_product_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
    query: Query[DataProductTransformationItemQueryParameters],
):
    """Get a data product transformation."""

    return 200, _service.get(
        principal=request.principal,
        task_id=task_id,
        uid=transformation_id,
        include=query.include,
    )


@data_product_transformation_router.patch(
    "/{transformation_id}",
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
def update_data_product_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
    data: DataProductTransformationPatchBody,
):
    """Update a data product transformation."""

    _service.update(
        principal=request.principal,
        task_id=task_id,
        uid=transformation_id,
        data=data,
    )

    return 204, None


@data_product_transformation_router.delete(
    "/{transformation_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def delete_data_product_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
):
    """Delete a data product transformation."""

    _service.delete(
        principal=request.principal,
        task_id=task_id,
        uid=transformation_id,
    )

    return 204, None
