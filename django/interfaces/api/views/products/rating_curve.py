import uuid

from ninja import Router, Path, Query
from django.http import HttpResponse

from interfaces.api.http.errors import raise_http_errors
from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import bearer_auth, session_auth, apikey_auth
from processing.products.services.rating_curve import RatingCurveService
from interfaces.api.schemas.products.rating_curve import (
    RatingCurveResponse,
    RatingCurvePostBody,
    RatingCurvePatchBody,
    RatingCurveQueryParameters,
)

rating_curve_router = Router(tags=["Rating Curves"])
rating_curve_service = RatingCurveService()


@rating_curve_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
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

    with raise_http_errors():
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
    auth=[session_auth, bearer_auth, apikey_auth],
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

    with raise_http_errors():
        rating_curve = rating_curve_service.create(
            principal=request.principal,
            thing=data.thing_id,
            **data.model_dump(exclude_unset=True, exclude={"thing_id"}),
        )

    return 201, rating_curve


@rating_curve_router.get(
    "/{rating_curve_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
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

    with raise_http_errors():
        rating_curve = rating_curve_service.get(
            rating_curve=rating_curve_id,
            principal=request.principal,
        )

    return 200, rating_curve


@rating_curve_router.patch(
    "/{rating_curve_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
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

    with raise_http_errors():
        rating_curve = rating_curve_service.update(
            rating_curve=rating_curve_id,
            principal=request.principal,
            **data.model_dump(exclude_unset=True),
        )

    return 200, rating_curve


@rating_curve_router.delete(
    "/{rating_curve_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
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

    with raise_http_errors():
        rating_curve_service.delete(
            rating_curve=rating_curve_id,
            principal=request.principal,
        )

    return 204, None
