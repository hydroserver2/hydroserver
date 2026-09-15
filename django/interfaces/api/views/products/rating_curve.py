import uuid

from ninja import Router, Path, Query

from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth
from interfaces.api.services.products.rating_curve import RatingCurveAPIService
from interfaces.api.schemas import PaginatedResponse, ItemResponse, CreatedResponse
from interfaces.api.schemas.products.rating_curve import (
    RatingCurveResponse,
    RatingCurvePostBody,
    RatingCurvePatchBody,
    RatingCurveQueryParameters,
    RatingCurveItemQueryParameters,
)

rating_curve_router = Router(tags=["Rating Curves"])
rating_curve_service = RatingCurveAPIService()


@rating_curve_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: PaginatedResponse[RatingCurveResponse],
        401: str,
    },
    by_alias=True,
)
def get_rating_curves(
    request: HydroServerHttpRequest,
    query: Query[RatingCurveQueryParameters],
):
    """
    Get rating curves accessible to the authenticated user.
    """

    return 200, rating_curve_service.list(
        principal=request.principal,
        offset=query.offset,
        limit=query.limit,
        sortby=query.sortby,
        filtering=query.dict(exclude_unset=True),
        include=query.include,
    )


@rating_curve_router.post(
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
def create_rating_curve(
    request: HydroServerHttpRequest,
    data: RatingCurvePostBody,
):
    """
    Create a new rating curve.
    """

    return 201, rating_curve_service.create(
        principal=request.principal,
        data=data,
    )


@rating_curve_router.get(
    "/{rating_curve_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: ItemResponse[RatingCurveResponse],
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_rating_curve(
    request: HydroServerHttpRequest,
    rating_curve_id: Path[uuid.UUID],
    query: Query[RatingCurveItemQueryParameters],
):
    """
    Get a rating curve.
    """

    return 200, rating_curve_service.get(
        principal=request.principal,
        uid=rating_curve_id,
        include=query.include,
    )


@rating_curve_router.patch(
    "/{rating_curve_id}",
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
def update_rating_curve(
    request: HydroServerHttpRequest,
    rating_curve_id: Path[uuid.UUID],
    data: RatingCurvePatchBody,
):
    """
    Update a rating curve.
    """

    rating_curve_service.update(
        principal=request.principal,
        uid=rating_curve_id,
        data=data,
    )

    return 204, None


@rating_curve_router.delete(
    "/{rating_curve_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        204: None,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def delete_rating_curve(
    request: HydroServerHttpRequest,
    rating_curve_id: Path[uuid.UUID],
):
    """
    Delete a rating curve.
    """

    rating_curve_service.delete(
        principal=request.principal,
        uid=rating_curve_id,
    )

    return 204, None
