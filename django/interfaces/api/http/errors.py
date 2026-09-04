import logging
from ninja.errors import HttpError

logger = logging.getLogger(__name__)


class BadRequestError(HttpError):
    def __init__(self, message="Bad Request"):
        super().__init__(400, message)


class UnauthorizedError(HttpError):
    def __init__(self, message="Unauthorized"):
        super().__init__(401, message)


class PermissionDeniedError(HttpError):
    def __init__(self, message="Forbidden"):
        super().__init__(403, message)


class NotFoundError(HttpError):
    def __init__(self, message="Not Found"):
        super().__init__(404, message)


class ConflictError(HttpError):
    def __init__(self, message="Conflict"):
        super().__init__(409, message)


class ServerError(HttpError):
    def __init__(self, message="Server Error"):
        super().__init__(500, message)
