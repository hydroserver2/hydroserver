import uuid
from typing import Optional
from ninja import Router, Path, Query
from django.http import HttpResponse
from django.db import transaction
from interfaces.http.auth import bearer_auth, session_auth, apikey_auth, anonymous_auth
from interfaces.http.request import HydroServerHttpRequest
from interfaces.api.schemas import VocabularyQueryParameters
from interfaces.api.schemas import (
    ObservedPropertySummaryResponse,
    ObservedPropertyDetailResponse,
    ObservedPropertyQueryParameters,
    ObservedPropertyPostBody,
    ObservedPropertyPatchBody,
)
from domains.sta.services import ObservedPropertyService

observed_property_router = Router(tags=["Observed Properties"])
observed_property_service = ObservedPropertyService()


@observed_property_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
    response={
        200: list[ObservedPropertySummaryResponse]
        | list[ObservedPropertyDetailResponse],
        401: str,
    },
    by_alias=True,
)
def get_observed_properties(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[ObservedPropertyQueryParameters],
):
    """
    Get public Observed Properties and Observed Properties associated with the authenticated user.
    """

    return 200, observed_property_service.list(
        principal=request.principal,
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_by=query.order_by,
        filtering=query.dict(exclude_unset=True),
        expand_related=query.expand_related,
    )


@observed_property_router.post(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: ObservedPropertySummaryResponse | ObservedPropertyDetailResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def create_observed_property(
    request: HydroServerHttpRequest,
    data: ObservedPropertyPostBody,
    expand_related: Optional[bool] = None,
):
    """
    Create a new Observed Property.
    """

    return 201, observed_property_service.create(
        principal=request.principal,
        data=data,
        expand_related=expand_related,
    )


@observed_property_router.get(
    "/variable-types", response={200: list[str]}, by_alias=True
)
def get_datastream_aggregation_statistics(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[VocabularyQueryParameters],
):
    """
    Get variable types.
    """

    return 200, observed_property_service.list_variable_types(
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_desc=query.order_desc,
    )


@observed_property_router.get(
    "/{observed_property_id}",
    auth=[session_auth, bearer_auth, apikey_auth, anonymous_auth],
    response={
        200: ObservedPropertySummaryResponse | ObservedPropertyDetailResponse,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_observed_property(
    request: HydroServerHttpRequest,
    observed_property_id: Path[uuid.UUID],
    expand_related: Optional[bool] = None,
):
    """
    Get an Observed Property.
    """

    return 200, observed_property_service.get(
        principal=request.principal,
        uid=observed_property_id,
        expand_related=expand_related,
    )


@observed_property_router.patch(
    "/{observed_property_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: ObservedPropertySummaryResponse | ObservedPropertyDetailResponse,
        400: str,
        401: str,
        403: str,
        422: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_observed_property(
    request: HydroServerHttpRequest,
    observed_property_id: Path[uuid.UUID],
    data: ObservedPropertyPatchBody,
    expand_related: Optional[bool] = None,
):
    """
    Update an Observed Property.
    """

    return 200, observed_property_service.update(
        principal=request.principal,
        uid=observed_property_id,
        data=data,
        expand_related=expand_related,
    )


@observed_property_router.delete(
    "/{observed_property_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
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
