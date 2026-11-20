import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_data_read_auth, oidc_data_write_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import ZReferenceAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.sta.vocabulary import (
    VocabularyQueryParameters,
    VocabularyItemQueryParameters,
)
from interfaces.api.schemas.sta.z_reference import (
    ZReferenceResponse,
    ZReferencePostBody,
    ZReferencePatchBody,
)

z_reference_router = Router(tags=["Z References"])
z_reference_service = ZReferenceAPIService()


@z_reference_router.get(
    "/items",
    auth=[session_auth, oidc_data_read_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[ZReferenceResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_z_references(
    request: HydroServerHttpRequest,
    query: Query[VocabularyQueryParameters],
):
    """
    Get z references.
    """

    return 200, z_reference_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
    )


@z_reference_router.post(
    "/items",
    auth=[session_auth, oidc_data_write_auth, apikey_auth, basic_auth],
    response={
        201: CreatedResponse,
        401: str,
        403: str,
        409: str,
    },
    by_alias=True,
)
@transaction.atomic
def create_z_reference(
    request: HydroServerHttpRequest,
    data: ZReferencePostBody,
):
    """
    Create a new z reference.
    """

    return 201, z_reference_service.create(
        principal=request.principal,
        data=data,
    )


@z_reference_router.get(
    "/items/{z_reference_id}",
    auth=[session_auth, oidc_data_read_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[ZReferenceResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_z_reference(
    request: HydroServerHttpRequest,
    z_reference_id: Path[uuid.UUID],
    query: Query[VocabularyItemQueryParameters],
):
    """
    Get a z reference.
    """

    return 200, z_reference_service.get(
        principal=request.principal,
        uid=z_reference_id,
    )


@z_reference_router.patch(
    "/items/{z_reference_id}",
    auth=[session_auth, oidc_data_write_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
        409: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_z_reference(
    request: HydroServerHttpRequest,
    z_reference_id: Path[uuid.UUID],
    data: ZReferencePatchBody,
):
    """
    Update a z reference.
    """

    z_reference_service.update(
        principal=request.principal,
        uid=z_reference_id,
        data=data,
    )
    return 204, None


@z_reference_router.delete(
    "/items/{z_reference_id}",
    auth=[session_auth, oidc_data_write_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_z_reference(
    request: HydroServerHttpRequest, z_reference_id: Path[uuid.UUID]
):
    """
    Delete a z reference.
    """

    return 204, z_reference_service.delete(
        principal=request.principal, uid=z_reference_id
    )
