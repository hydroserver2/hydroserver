import uuid

from ninja import Router, Path, Query
from django.http import HttpResponse

from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import session_auth, oidc_auth, apikey_auth, basic_auth
from interfaces.api.services.products.rating_curve import RatingCurveAPIService
from interfaces.api.schemas.products.rating_curve import (
    RatingCurveResponse,
    RatingCurvePostBody,
    RatingCurvePatchBody,
    RatingCurveQueryParameters,
)

rating_curve_router = Router(tags=["Rating Curves"])
rating_curve_service = RatingCurveAPIService()


@rating_curve_router.get(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: list[RatingCurveResponse],
        401: str,
    },
    by_alias=True,
)
def get_rating_curves(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[RatingCurveQueryParameters],
):
    """
    Get rating curves accessible to the authenticated user.
    """

    count, rating_curves = rating_curve_service.get_collection(
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

    return 200, rating_curves


@rating_curve_router.post(
    "",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        201: RatingCurveResponse,
        400: str,
        401: str,
        403: str,
        404: str,
        422: str,
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

    rating_curve = rating_curve_service.create(
        principal=request.principal,
        monitoring_site=data.monitoring_site_id,
        **data.model_dump(exclude_unset=True, exclude={"monitoring_site_id"}),
    )

    return 201, rating_curve


@rating_curve_router.get(
    "/{rating_curve_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: RatingCurveResponse,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_rating_curve(
    request: HydroServerHttpRequest,
    rating_curve_id: Path[uuid.UUID],
):
    """
    Get a rating curve.
    """

    rating_curve = rating_curve_service.get(
        rating_curve=rating_curve_id,
        principal=request.principal,
    )

    return 200, rating_curve


@rating_curve_router.patch(
    "/{rating_curve_id}",
    auth=[session_auth, oidc_auth, apikey_auth, basic_auth],
    response={
        200: RatingCurveResponse,
        400: str,
        401: str,
        403: str,
        404: str,
        422: str,
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

    rating_curve = rating_curve_service.update(
        rating_curve=rating_curve_id,
        principal=request.principal,
        **data.model_dump(exclude_unset=True),
    )

    return 200, rating_curve


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
        rating_curve=rating_curve_id,
        principal=request.principal,
    )

    return 204, None
