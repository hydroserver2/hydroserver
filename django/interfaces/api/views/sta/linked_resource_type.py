import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import LinkedResourceTypeAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.sta.controlled_vocabulary import (
    ControlledVocabularyQueryParameters,
    ControlledVocabularyItemQueryParameters,
)
from interfaces.api.schemas.sta.linked_resource_type import (
    LinkedResourceTypeResponse,
    LinkedResourceTypePostBody,
    LinkedResourceTypePatchBody,
)

linked_resource_type_router = Router(tags=["Linked Resource Types"])
linked_resource_type_service = LinkedResourceTypeAPIService()


@linked_resource_type_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[LinkedResourceTypeResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_linked_resource_types(
    request: HydroServerHttpRequest,
    query: Query[ControlledVocabularyQueryParameters],
):
    """
    Get public Linked Resource Types and Linked Resource Types associated with the authenticated user.
    """

    return 200, linked_resource_type_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@linked_resource_type_router.post(
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
def create_linked_resource_type(
    request: HydroServerHttpRequest,
    data: LinkedResourceTypePostBody,
):
    """
    Create a new Linked Resource Type.
    """

    return 201, linked_resource_type_service.create(
        principal=request.principal,
        data=data,
    )


@linked_resource_type_router.get(
    "/{linked_resource_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[LinkedResourceTypeResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_linked_resource_type(
    request: HydroServerHttpRequest,
    linked_resource_type_id: Path[uuid.UUID],
    query: Query[ControlledVocabularyItemQueryParameters],
):
    """
    Get a Linked Resource Type.
    """

    return 200, linked_resource_type_service.get(
        principal=request.principal,
        uid=linked_resource_type_id,
        include=query.include,
    )


@linked_resource_type_router.patch(
    "/{linked_resource_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_linked_resource_type(
    request: HydroServerHttpRequest,
    linked_resource_type_id: Path[uuid.UUID],
    data: LinkedResourceTypePatchBody,
):
    """
    Update a Linked Resource Type.
    """

    linked_resource_type_service.update(
        principal=request.principal,
        uid=linked_resource_type_id,
        data=data,
    )
    return 204, None


@linked_resource_type_router.delete(
    "/{linked_resource_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_linked_resource_type(
    request: HydroServerHttpRequest, linked_resource_type_id: Path[uuid.UUID]
):
    """
    Delete a Linked Resource Type.
    """

    return 204, linked_resource_type_service.delete(
        principal=request.principal, uid=linked_resource_type_id
    )
