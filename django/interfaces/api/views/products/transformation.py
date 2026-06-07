import uuid

from ninja import Router, Path, Query
from django.http import HttpResponse

from core.types import Unset
from interfaces.api.http.errors import raise_http_errors
from interfaces.api.http.response import apply_response_pagination_headers
from interfaces.api.http.request import HydroServerHttpRequest
from interfaces.auth.security import bearer_auth, session_auth, apikey_auth
from processing.products.services.transformation import (DataProductTransformationService, TransformationInput,
                                                         TransformationInputPatch)
from interfaces.api.schemas.products.transformation import (
    DataProductTransformationTypeQueryParameters,
    RatingCurveTransformationSummaryResponse,
    RatingCurveTransformationPostBody,
    RatingCurveTransformationPatchBody,
    ExpressionTransformationSummaryResponse,
    ExpressionTransformationPostBody,
    ExpressionTransformationPatchBody,
    CompositeExpressionTransformationSummaryResponse,
    CompositeExpressionTransformationPostBody,
    CompositeExpressionTransformationPatchBody,
    AggregationTransformationSummaryResponse,
    AggregationTransformationPostBody,
    AggregationTransformationPatchBody,
)

_service = DataProductTransformationService()
_auth = [session_auth, bearer_auth, apikey_auth]


# ---------------------------------------------------------------------------
# Rating Curve
# ---------------------------------------------------------------------------

rating_curve_transformation_router = Router(tags=["Rating Curve Transformations"])


@rating_curve_transformation_router.get(
    "",
    auth=_auth,
    response={200: list[RatingCurveTransformationSummaryResponse], 401: str, 403: str, 404: str},
    by_alias=True,
)
def get_rating_curve_transformations(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    task_id: Path[uuid.UUID],
    query: Query[DataProductTransformationTypeQueryParameters],
):
    """Get rating curve transformations for a data product task."""

    with raise_http_errors():
        count, transformations = _service.get_collection(
            task=task_id,
            principal=request.principal,
            transformation_type=["rating_curve"],
            order_by=[f.orm_field for f in query.order_by],
            **query.model_dump(exclude_unset=True, exclude={"order_by", "output_datastream", "input_datastream"}),
            **({"output_datastream": query.output_datastream} if "output_datastream" in query.model_fields_set else {}),
            **({"input_datastream": query.input_datastream} if "input_datastream" in query.model_fields_set else {}),
        )

    apply_response_pagination_headers(response=response, count=count, page=query.page, page_size=query.page_size)

    return 200, transformations


@rating_curve_transformation_router.post(
    "",
    auth=_auth,
    response={201: RatingCurveTransformationSummaryResponse, 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def create_rating_curve_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    data: RatingCurveTransformationPostBody,
):
    """Create a rating curve transformation on a data product task."""

    with raise_http_errors():
        transformation = _service.create(
            task=task_id,
            principal=request.principal,
            transformation_type="rating_curve",
            output_datastream=data.output_datastream,
            input_datastreams=[TransformationInput(datastream=data.input_datastream)],
            **data.model_dump(
                exclude_unset=True,
                exclude={"uid", "output_datastream", "input_datastream"},
            ),
            **({"uid": data.uid} if data.uid is not Unset else {}),
        )

    return 201, transformation


@rating_curve_transformation_router.get(
    "/{transformation_id}",
    auth=_auth,
    response={200: RatingCurveTransformationSummaryResponse, 401: str, 403: str, 404: str},
    by_alias=True,
)
def get_rating_curve_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
):
    """Get a rating curve transformation."""

    with raise_http_errors():
        transformation = _service.get(
            transformation=transformation_id, task=task_id, principal=request.principal, action="view",
        )

    return 200, transformation


@rating_curve_transformation_router.patch(
    "/{transformation_id}",
    auth=_auth,
    response={200: RatingCurveTransformationSummaryResponse, 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def update_rating_curve_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
    data: RatingCurveTransformationPatchBody,
):
    """Update a rating curve transformation."""

    update_kwargs = data.model_dump(exclude_unset=True, exclude={"input_datastream"})

    if "input_datastream" in data.model_fields_set:
        update_kwargs["input_datastreams"] = [TransformationInput(datastream=data.input_datastream)]

    with raise_http_errors():
        transformation = _service.update(
            transformation=transformation_id, task=task_id, principal=request.principal, **update_kwargs,
        )

    return 200, transformation


@rating_curve_transformation_router.delete(
    "/{transformation_id}",
    auth=_auth,
    response={204: None, 401: str, 403: str, 404: str},
    by_alias=True,
)
def delete_rating_curve_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
):
    """Delete a rating curve transformation."""

    with raise_http_errors():
        _service.delete(transformation=transformation_id, task=task_id, principal=request.principal)

    return 204, None


# ---------------------------------------------------------------------------
# Expression
# ---------------------------------------------------------------------------

expression_transformation_router = Router(tags=["Expression Transformations"])


@expression_transformation_router.get(
    "",
    auth=_auth,
    response={200: list[ExpressionTransformationSummaryResponse], 401: str, 403: str, 404: str},
    by_alias=True,
)
def get_expression_transformations(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    task_id: Path[uuid.UUID],
    query: Query[DataProductTransformationTypeQueryParameters],
):
    """Get expression transformations for a data product task."""

    with raise_http_errors():
        count, transformations = _service.get_collection(
            task=task_id,
            principal=request.principal,
            transformation_type=["expression"],
            order_by=[f.orm_field for f in query.order_by],
            **query.model_dump(exclude_unset=True, exclude={"order_by", "output_datastream", "input_datastream"}),
            **({"output_datastream": query.output_datastream} if "output_datastream" in query.model_fields_set else {}),
            **({"input_datastream": query.input_datastream} if "input_datastream" in query.model_fields_set else {}),
        )

    apply_response_pagination_headers(response=response, count=count, page=query.page, page_size=query.page_size)

    return 200, transformations


@expression_transformation_router.post(
    "",
    auth=_auth,
    response={201: ExpressionTransformationSummaryResponse, 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def create_expression_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    data: ExpressionTransformationPostBody,
):
    """Create an expression transformation on a data product task."""

    with raise_http_errors():
        transformation = _service.create(
            task=task_id,
            principal=request.principal,
            transformation_type="expression",
            output_datastream=data.output_datastream,
            input_datastreams=[
                TransformationInput(
                    datastream=data.input_datastream,
                    variable_name=data.variable_name
                )
            ],
            **data.model_dump(
                exclude_unset=True,
                exclude={"uid", "output_datastream", "input_datastream", "variable_name"},
            ),
            **({"uid": data.uid} if data.uid is not Unset else {}),
        )

    return 201, transformation


@expression_transformation_router.get(
    "/{transformation_id}",
    auth=_auth,
    response={200: ExpressionTransformationSummaryResponse, 401: str, 403: str, 404: str},
    by_alias=True,
)
def get_expression_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
):
    """Get an expression transformation."""

    with raise_http_errors():
        transformation = _service.get(
            transformation=transformation_id, task=task_id, principal=request.principal, action="view",
        )

    return 200, transformation


@expression_transformation_router.patch(
    "/{transformation_id}",
    auth=_auth,
    response={200: ExpressionTransformationSummaryResponse, 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def update_expression_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
    data: ExpressionTransformationPatchBody,
):
    """Update an expression transformation."""

    update_kwargs = data.model_dump(exclude_unset=True, exclude={"input_datastream", "variable_name"})

    if "input_datastream" in data.model_fields_set or "variable_name" in data.model_fields_set:
        patch_kwargs = {}
        if "input_datastream" in data.model_fields_set:
            patch_kwargs["datastream"] = data.input_datastream
        if "variable_name" in data.model_fields_set:
            patch_kwargs["variable_name"] = data.variable_name
        update_kwargs["input_datastreams"] = [TransformationInputPatch(**patch_kwargs)]

    with raise_http_errors():
        transformation = _service.update(
            transformation=transformation_id, task=task_id, principal=request.principal, **update_kwargs,
        )

    return 200, transformation


@expression_transformation_router.delete(
    "/{transformation_id}",
    auth=_auth,
    response={204: None, 401: str, 403: str, 404: str},
    by_alias=True,
)
def delete_expression_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
):
    """Delete an expression transformation."""

    with raise_http_errors():
        _service.delete(transformation=transformation_id, task=task_id, principal=request.principal)

    return 204, None


# ---------------------------------------------------------------------------
# Composite Expression
# ---------------------------------------------------------------------------

composite_expression_transformation_router = Router(tags=["Composite Expression Transformations"])


@composite_expression_transformation_router.get(
    "",
    auth=_auth,
    response={200: list[CompositeExpressionTransformationSummaryResponse], 401: str, 403: str, 404: str},
    by_alias=True,
)
def get_composite_expression_transformations(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    task_id: Path[uuid.UUID],
    query: Query[DataProductTransformationTypeQueryParameters],
):
    """Get composite expression transformations for a data product task."""

    with raise_http_errors():
        count, transformations = _service.get_collection(
            task=task_id,
            principal=request.principal,
            transformation_type=["composite_expression"],
            order_by=[f.orm_field for f in query.order_by],
            **query.model_dump(exclude_unset=True, exclude={"order_by", "output_datastream", "input_datastream"}),
            **({"output_datastream": query.output_datastream} if "output_datastream" in query.model_fields_set else {}),
            **({"input_datastream": query.input_datastream} if "input_datastream" in query.model_fields_set else {}),
        )

    apply_response_pagination_headers(response=response, count=count, page=query.page, page_size=query.page_size)

    return 200, transformations


@composite_expression_transformation_router.post(
    "",
    auth=_auth,
    response={201: CompositeExpressionTransformationSummaryResponse, 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def create_composite_expression_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    data: CompositeExpressionTransformationPostBody,
):
    """Create a composite expression transformation on a data product task."""

    with raise_http_errors():
        transformation = _service.create(
            task=task_id,
            principal=request.principal,
            transformation_type="composite_expression",
            output_datastream=data.output_datastream,
            input_datastreams=[TransformationInput(**inp.model_dump()) for inp in data.input_datastreams],
            **data.model_dump(
                exclude_unset=True,
                exclude={"uid", "output_datastream", "input_datastreams"},
            ),
            **({"uid": data.uid} if data.uid is not Unset else {}),
        )

    return 201, transformation


@composite_expression_transformation_router.get(
    "/{transformation_id}",
    auth=_auth,
    response={200: CompositeExpressionTransformationSummaryResponse, 401: str, 403: str, 404: str},
    by_alias=True,
)
def get_composite_expression_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
):
    """Get a composite expression transformation."""

    with raise_http_errors():
        transformation = _service.get(
            transformation=transformation_id, task=task_id, principal=request.principal, action="view",
        )

    return 200, transformation


@composite_expression_transformation_router.patch(
    "/{transformation_id}",
    auth=_auth,
    response={200: CompositeExpressionTransformationSummaryResponse, 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def update_composite_expression_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
    data: CompositeExpressionTransformationPatchBody,
):
    """Update a composite expression transformation."""

    update_kwargs = data.model_dump(exclude_unset=True, exclude={"input_datastreams"})

    if "input_datastreams" in data.model_fields_set:
        update_kwargs["input_datastreams"] = [TransformationInput(**inp.model_dump()) for inp in data.input_datastreams]

    with raise_http_errors():
        transformation = _service.update(
            transformation=transformation_id, task=task_id, principal=request.principal, **update_kwargs,
        )

    return 200, transformation


@composite_expression_transformation_router.delete(
    "/{transformation_id}",
    auth=_auth,
    response={204: None, 401: str, 403: str, 404: str},
    by_alias=True,
)
def delete_composite_expression_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
):
    """Delete a composite expression transformation."""

    with raise_http_errors():
        _service.delete(transformation=transformation_id, task=task_id, principal=request.principal)

    return 204, None


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

aggregation_transformation_router = Router(tags=["Aggregation Transformations"])


@aggregation_transformation_router.get(
    "",
    auth=_auth,
    response={200: list[AggregationTransformationSummaryResponse], 401: str, 403: str, 404: str},
    by_alias=True,
)
def get_aggregation_transformations(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    task_id: Path[uuid.UUID],
    query: Query[DataProductTransformationTypeQueryParameters],
):
    """Get aggregation transformations for a data product task."""

    with raise_http_errors():
        count, transformations = _service.get_collection(
            task=task_id,
            principal=request.principal,
            transformation_type=["aggregation"],
            order_by=[f.orm_field for f in query.order_by],
            **query.model_dump(exclude_unset=True, exclude={"order_by", "output_datastream", "input_datastream"}),
            **({"output_datastream": query.output_datastream} if "output_datastream" in query.model_fields_set else {}),
            **({"input_datastream": query.input_datastream} if "input_datastream" in query.model_fields_set else {}),
        )

    apply_response_pagination_headers(response=response, count=count, page=query.page, page_size=query.page_size)

    return 200, transformations


@aggregation_transformation_router.post(
    "",
    auth=_auth,
    response={201: AggregationTransformationSummaryResponse, 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def create_aggregation_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    data: AggregationTransformationPostBody,
):
    """Create an aggregation transformation on a data product task."""

    with raise_http_errors():
        transformation = _service.create(
            task=task_id,
            principal=request.principal,
            transformation_type="aggregation",
            output_datastream=data.output_datastream,
            input_datastreams=[TransformationInput(datastream=data.input_datastream)],
            **data.model_dump(
                exclude_unset=True,
                exclude={"uid", "output_datastream", "input_datastream"},
            ),
            **({"uid": data.uid} if data.uid is not Unset else {}),
        )

    return 201, transformation


@aggregation_transformation_router.get(
    "/{transformation_id}",
    auth=_auth,
    response={200: AggregationTransformationSummaryResponse, 401: str, 403: str, 404: str},
    by_alias=True,
)
def get_aggregation_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
):
    """Get an aggregation transformation."""

    with raise_http_errors():
        transformation = _service.get(
            transformation=transformation_id, task=task_id, principal=request.principal, action="view",
        )

    return 200, transformation


@aggregation_transformation_router.patch(
    "/{transformation_id}",
    auth=_auth,
    response={200: AggregationTransformationSummaryResponse, 400: str, 401: str, 403: str, 404: str, 422: str},
    by_alias=True,
)
def update_aggregation_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
    data: AggregationTransformationPatchBody,
):
    """Update an aggregation transformation."""

    update_kwargs = data.model_dump(exclude_unset=True, exclude={"input_datastream"})

    if "input_datastream" in data.model_fields_set:
        update_kwargs["input_datastreams"] = [TransformationInput(datastream=data.input_datastream)]

    with raise_http_errors():
        transformation = _service.update(
            transformation=transformation_id, task=task_id, principal=request.principal, **update_kwargs,
        )

    return 200, transformation


@aggregation_transformation_router.delete(
    "/{transformation_id}",
    auth=_auth,
    response={204: None, 401: str, 403: str, 404: str},
    by_alias=True,
)
def delete_aggregation_transformation(
    request: HydroServerHttpRequest,
    task_id: Path[uuid.UUID],
    transformation_id: Path[uuid.UUID],
):
    """Delete an aggregation transformation."""

    with raise_http_errors():
        _service.delete(transformation=transformation_id, task=task_id, principal=request.principal)

    return 204, None
