import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import ObservedPropertyTypeAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.sta.controlled_vocabulary import (
    ControlledVocabularyQueryParameters,
    ControlledVocabularyItemQueryParameters,
)
from interfaces.api.schemas.sta.observed_property_type import (
    ObservedPropertyTypeResponse,
    ObservedPropertyTypePostBody,
    ObservedPropertyTypePatchBody,
)

observed_property_type_router = Router(tags=["Observed Property Types"])
observed_property_type_service = ObservedPropertyTypeAPIService()


@observed_property_type_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[ObservedPropertyTypeResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_observed_property_types(
    request: HydroServerHttpRequest,
    query: Query[ControlledVocabularyQueryParameters],
):
    """
    Get public Observed Property Types and Observed Property Types associated with the authenticated user.
    """

    return 200, observed_property_type_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@observed_property_type_router.post(
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
def create_observed_property_type(
    request: HydroServerHttpRequest,
    data: ObservedPropertyTypePostBody,
):
    """
    Create a new Observed Property Type.
    """

    return 201, observed_property_type_service.create(
        principal=request.principal,
        data=data,
    )


@observed_property_type_router.get(
    "/{observed_property_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[ObservedPropertyTypeResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_observed_property_type(
    request: HydroServerHttpRequest,
    observed_property_type_id: Path[uuid.UUID],
    query: Query[ControlledVocabularyItemQueryParameters],
):
    """
    Get an Observed Property Type.
    """

    return 200, observed_property_type_service.get(
        principal=request.principal,
        uid=observed_property_type_id,
        include=query.include,
    )


@observed_property_type_router.patch(
    "/{observed_property_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_observed_property_type(
    request: HydroServerHttpRequest,
    observed_property_type_id: Path[uuid.UUID],
    data: ObservedPropertyTypePatchBody,
):
    """
    Update an Observed Property Type.
    """

    observed_property_type_service.update(
        principal=request.principal,
        uid=observed_property_type_id,
        data=data,
    )
    return 204, None


@observed_property_type_router.delete(
    "/{observed_property_type_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_observed_property_type(
    request: HydroServerHttpRequest, observed_property_type_id: Path[uuid.UUID]
):
    """
    Delete an Observed Property Type.
    """

    return 204, observed_property_type_service.delete(
        principal=request.principal, uid=observed_property_type_id
    )
