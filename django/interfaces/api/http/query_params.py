from functools import wraps
from typing import Callable

from django.http import HttpRequest, HttpResponseBase
from ninja.operation import Operation

from interfaces.api.http.negotiation import negotiated_query_params


def declared_query_params(operation: Operation) -> frozenset[str]:
    """
    Returns the query parameter names an operation declares, as they appear in the request URI
    and in the OpenAPI document (aliases such as 'format', not the Python field names).
    """

    names: set[str] = set()

    for model in operation.models:
        if getattr(model, "__ninja_param_source__", None) != "query":
            continue

        flatten_map = getattr(model, "__ninja_flatten_map__", None)
        if flatten_map is None:
            raise TypeError(
                f"Cannot determine the query parameters of '{operation.view_func.__name__}': "
                f"{model.__name__} has no flatten map."
            )

        names.update(flatten_map)

    return frozenset(names)


def reject_unknown_query_params(run: Callable[..., HttpResponseBase]) -> Callable[..., HttpResponseBase]:
    """
    Ninja view-mode decorator that responds 400 to requests with query parameters the operation
    doesn't declare (OGC API - Features Core Req 8, /req/core/query-param-unknown).

    Ninja ignores undeclared query parameters, so without this a misspelled filter such as
    '?workspaceId=' silently returns unfiltered results. View-mode decorators wrap the bound
    Operation.run, which is how the operation's declared parameters are found.
    """

    operation = getattr(run, "__self__", None)
    if not isinstance(operation, Operation):
        raise TypeError(
            "reject_unknown_query_params must be registered with mode='view' before any other "
            "view decorator, so it wraps Operation.run directly."
        )

    allowed = declared_query_params(operation)

    @wraps(run)
    def wrapper(request: HttpRequest, **kwargs) -> HttpResponseBase:
        request_allowed = allowed | negotiated_query_params(request)
        unknown = sorted(set(request.GET) - request_allowed)

        if unknown:
            message = f"Unknown query parameter(s): {', '.join(unknown)}."
            message += (
                f" Allowed: {', '.join(sorted(request_allowed))}."
                if request_allowed else " This operation accepts none."
            )
            return operation.api.create_response(request, {"message": message}, status=400)

        return run(request, **kwargs)

    return wrapper
