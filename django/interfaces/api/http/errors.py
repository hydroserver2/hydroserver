import logging
from contextlib import contextmanager
from django.db import IntegrityError
from ninja.errors import HttpError

logger = logging.getLogger(__name__)


@contextmanager
def raise_http_errors():
    try:
        yield
    except ValueError as e:
        raise HttpError(400, str(e))
    except PermissionError as e:
        raise HttpError(403, str(e))
    except LookupError as e:
        raise HttpError(404, str(e))
    except IntegrityError as e:
        raise HttpError(409, str(e))
    except Exception as e:
        logger.exception(e)
        raise HttpError(500, "Encountered an unexpected error.")
