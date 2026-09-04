import logging

from django.core.exceptions import ValidationError as DjangoValidationError, ObjectDoesNotExist
from django.db import IntegrityError, DataError
from django.db.models.deletion import ProtectedError

logger = logging.getLogger(__name__)


def http_error_handler(request, exc, api):
    return api.create_response(
        request,
        {"message": exc.message},
        status=exc.status_code,
    )


def validation_error_handler(request, exc, api):
    return api.create_response(
        request,
        {"message": "; ".join(exc.messages)},
        status=422,
    )


def conflict_error_handler(request, exc, api):
    return api.create_response(
        request,
        {"message": str(exc)},
        status=409,
    )


def not_found_error_handler(request, exc, api):
    return api.create_response(
        request,
        {"message": str(exc)},
        status=404,
    )


def unhandled_error_handler(request, exc, api):
    logger.exception(exc)
    return api.create_response(
        request,
        {"message": "Internal Server Error"},
        status=500,
    )


def register(api):
    """Register all exception handlers on the given NinjaAPI instance."""

    from functools import partial
    from interfaces.api.http.errors import (
        BadRequestError, UnauthorizedError, PermissionDeniedError, NotFoundError, ConflictError, ServerError
    )

    for exc_class in (
        BadRequestError, UnauthorizedError, PermissionDeniedError, NotFoundError, ConflictError, ServerError
    ):
        api.add_exception_handler(exc_class, partial(http_error_handler, api=api))

    api.add_exception_handler(DjangoValidationError, partial(validation_error_handler, api=api))

    for exc_class in (IntegrityError, DataError, ProtectedError):
        api.add_exception_handler(exc_class, partial(conflict_error_handler, api=api))

    api.add_exception_handler(ObjectDoesNotExist, partial(not_found_error_handler, api=api))

    api.add_exception_handler(Exception, partial(unhandled_error_handler, api=api))