import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import ObservedPropertyAPIService
from interfaces.api.schemas import VocabularyQueryParameters
from interfaces.api.schemas import (
    ObservedPropertyResponse,
    ObservedPropertyPostBody,
    ObservedPropertyPatchBody,
    ObservedPropertyQueryParameters,
    ObservedPropertyItemQueryParameters,
    PaginatedResponse,
    ItemResponse,
    CreatedResponse,
)

observed_property_router = Router(tags=["Observed Properties"])
observed_property_service = ObservedPropertyAPIService()


@observed_property_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[ObservedPropertyResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_observed_properties(
    request: HydroServerHttpRequest,
    query: Query[ObservedPropertyQueryParameters],
):
    """
    Get public Observed Properties and Observed Properties associated with the authenticated user.
    """

    return 200, observed_property_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@observed_property_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: CreatedResponse,
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def create_observed_property(
    request: HydroServerHttpRequest,
    data: ObservedPropertyPostBody,
):
    """
    Create a new Observed Property.
    """

    return 201, observed_property_service.create(
        principal=request.principal,
        data=data,
    )


@observed_property_router.get(
    "/variable-types", response={200: PaginatedResponse[str]}, by_alias=True
)
def get_datastream_aggregation_statistics(
    request: HydroServerHttpRequest,
    query: Query[VocabularyQueryParameters],
):
    """
    Get variable types.
    """

    return 200, observed_property_service.list_variable_types(
        offset=query.offset,
        limit=query.limit,
        order_desc=query.order_desc,
    )


@observed_property_router.get(
    "/{observed_property_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[ObservedPropertyResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_observed_property(
    request: HydroServerHttpRequest,
    observed_property_id: Path[uuid.UUID],
    query: Query[ObservedPropertyItemQueryParameters],
):
    """
    Get an Observed Property.
    """

    return 200, observed_property_service.get(
        principal=request.principal,
        uid=observed_property_id,
        include=query.include,
    )


@observed_property_router.patch(
    "/{observed_property_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_observed_property(
    request: HydroServerHttpRequest,
    observed_property_id: Path[uuid.UUID],
    data: ObservedPropertyPatchBody,
):
    """
    Update an Observed Property.
    """

    observed_property_service.update(
        principal=request.principal,
        uid=observed_property_id,
        data=data,
    )

    return 204, None


@observed_property_router.delete(
    "/{observed_property_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
        409: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_observed_property(
    request: HydroServerHttpRequest, observed_property_id: Path[uuid.UUID]
):
    """
    Delete an Observed Property.
    """

    return 204, observed_property_service.delete(
        principal=request.principal, uid=observed_property_id
    )
