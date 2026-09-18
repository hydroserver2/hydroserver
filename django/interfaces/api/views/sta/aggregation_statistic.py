import uuid

from ninja import Router, Path, Query
from django.db import transaction

from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.api.services.sta import AggregationStatisticAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.sta.controlled_vocabulary import (
    ControlledVocabularyQueryParameters,
    ControlledVocabularyItemQueryParameters,
)
from interfaces.api.schemas.sta.aggregation_statistic import (
    AggregationStatisticResponse,
    AggregationStatisticPostBody,
    AggregationStatisticPatchBody,
)

aggregation_statistic_router = Router(tags=["Aggregation Statistics"])
aggregation_statistic_service = AggregationStatisticAPIService()


@aggregation_statistic_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: PaginatedResponse[AggregationStatisticResponse],
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_aggregation_statistics(
    request: HydroServerHttpRequest,
    query: Query[ControlledVocabularyQueryParameters],
):
    """
    Get public Aggregation Statistics and Aggregation Statistics associated with the authenticated user.
    """

    return 200, aggregation_statistic_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@aggregation_statistic_router.post(
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
def create_aggregation_statistic(
    request: HydroServerHttpRequest,
    data: AggregationStatisticPostBody,
):
    """
    Create a new Aggregation Statistic.
    """

    return 201, aggregation_statistic_service.create(
        principal=request.principal,
        data=data,
    )


@aggregation_statistic_router.get(
    "/{aggregation_statistic_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth, anonymous_auth],
    response={
        200: ItemResponse[AggregationStatisticResponse],
        400: str,
        401: str,
        403: str,
    },
    by_alias=True,
    exclude_unset=True,
)
def get_aggregation_statistic(
    request: HydroServerHttpRequest,
    aggregation_statistic_id: Path[uuid.UUID],
    query: Query[ControlledVocabularyItemQueryParameters],
):
    """
    Get an Aggregation Statistic.
    """

    return 200, aggregation_statistic_service.get(
        principal=request.principal,
        uid=aggregation_statistic_id,
        include=query.include,
    )


@aggregation_statistic_router.patch(
    "/{aggregation_statistic_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def update_aggregation_statistic(
    request: HydroServerHttpRequest,
    aggregation_statistic_id: Path[uuid.UUID],
    data: AggregationStatisticPatchBody,
):
    """
    Update an Aggregation Statistic.
    """

    aggregation_statistic_service.update(
        principal=request.principal,
        uid=aggregation_statistic_id,
        data=data,
    )
    return 204, None


@aggregation_statistic_router.delete(
    "/{aggregation_statistic_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
    },
    by_alias=True,
)
@transaction.atomic
def delete_aggregation_statistic(
    request: HydroServerHttpRequest, aggregation_statistic_id: Path[uuid.UUID]
):
    """
    Delete an Aggregation Statistic.
    """

    return 204, aggregation_statistic_service.delete(
        principal=request.principal, uid=aggregation_statistic_id
    )
