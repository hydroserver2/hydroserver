import uuid

from ninja import Router, Path, Query
from django.http import HttpResponse

from interfaces.api.http.errors import raise_http_errors
from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import bearer_auth, session_auth, apikey_auth
from processing.products.services.expression import ExpressionService
from interfaces.api.schemas.products.expression import (
    ExpressionResponse,
    ExpressionPostBody,
    ExpressionPatchBody,
    ExpressionQueryParameters,
)

expression_router = Router(tags=["Expressions"])
expression_service = ExpressionService()


@expression_router.get(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: list[ExpressionResponse],
        401: str,
    },
    by_alias=True,
)
def get_expressions(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[ExpressionQueryParameters],
):
    """
    Get expressions accessible to the authenticated user.
    """

    with raise_http_errors():
        count, expressions = expression_service.get_collection(
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

    return 200, expressions


@expression_router.post(
    "",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        201: ExpressionResponse,
        400: str,
        401: str,
        403: str,
        404: str,
        422: str,
    },
    by_alias=True,
)
def create_expression(
    request: HydroServerHttpRequest,
    data: ExpressionPostBody,
):
    """
    Create a new expression.
    """

    with raise_http_errors():
        expression = expression_service.create(
            principal=request.principal,
            thing=data.thing_id,
            **data.model_dump(exclude_unset=True, exclude={"thing_id"}),
        )

    return 201, expression


@expression_router.get(
    "/{expression_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: ExpressionResponse,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def get_expression(
    request: HydroServerHttpRequest,
    expression_id: Path[uuid.UUID],
):
    """
    Get an expression.
    """

    with raise_http_errors():
        expression = expression_service.get(
            expression=expression_id,
            principal=request.principal,
        )

    return 200, expression


@expression_router.patch(
    "/{expression_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        200: ExpressionResponse,
        400: str,
        401: str,
        403: str,
        404: str,
        422: str,
    },
    by_alias=True,
)
def update_expression(
    request: HydroServerHttpRequest,
    expression_id: Path[uuid.UUID],
    data: ExpressionPatchBody,
):
    """
    Update an expression.
    """

    with raise_http_errors():
        expression = expression_service.update(
            expression=expression_id,
            principal=request.principal,
            **data.model_dump(exclude_unset=True),
        )

    return 200, expression


@expression_router.delete(
    "/{expression_id}",
    auth=[session_auth, bearer_auth, apikey_auth],
    response={
        204: None,
        401: str,
        403: str,
        404: str,
    },
    by_alias=True,
)
def delete_expression(
    request: HydroServerHttpRequest,
    expression_id: Path[uuid.UUID],
):
    """
    Delete an expression.
    """

    with raise_http_errors():
        expression_service.delete(
            expression=expression_id,
            principal=request.principal,
        )

    return 204, None
