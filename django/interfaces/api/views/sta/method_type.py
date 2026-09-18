import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import MethodTypeAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.sta.controlled_vocabulary import (
    ControlledVocabularyQueryParameters,
    ControlledVocabularyItemQueryParameters,
)
from interfaces.api.schemas.sta.method_type import (
    MethodTypeResponse,
    MethodTypePostBody,
    MethodTypePatchBody,
)

method_type_router = Router(tags=["Method Types"])
method_type_service = MethodTypeAPIService()


@method_type_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[MethodTypeResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_method_types(
    request: HydroServerHttpRequest,
    query: Query[ControlledVocabularyQueryParameters],
):
    """
    Get public Method Types and Method Types associated with the authenticated user.
    """

    return 200, method_type_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@method_type_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: CreatedResponse,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def create_method_type(
    request: HydroServerHttpRequest,
    data: MethodTypePostBody,
):
    """
    Create a new Method Type.
    """

    return 201, method_type_service.create(
        principal=request.principal,
        data=data,
    )


@method_type_router.get(
    "/{method_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[MethodTypeResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_method_type(
    request: HydroServerHttpRequest,
    method_type_id: Path[uuid.UUID],
    query: Query[ControlledVocabularyItemQueryParameters],
):
    """
    Get a Method Type.
    """

    return 200, method_type_service.get(
        principal=request.principal,
        uid=method_type_id,
        include=query.include,
    )


@method_type_router.patch(
    "/{method_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_method_type(
    request: HydroServerHttpRequest,
    method_type_id: Path[uuid.UUID],
    data: MethodTypePatchBody,
):
    """
    Update a Method Type.
    """

    method_type_service.update(
        principal=request.principal,
        uid=method_type_id,
        data=data,
    )
    return 204, None


@method_type_router.delete(
    "/{method_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_method_type(
    request: HydroServerHttpRequest, method_type_id: Path[uuid.UUID]
):
    """
    Delete a Method Type.
    """

    return 204, method_type_service.delete(
        principal=request.principal, uid=method_type_id
    )
