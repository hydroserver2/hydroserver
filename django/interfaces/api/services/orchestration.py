from django.conf import settings
from interfaces.api.http.errors import NotImplementedHttpError


ORCHESTRATION_DISABLED_MESSAGE = "Job orchestration is not enabled on this HydroServer instance."


def require_orchestration_enabled():
    """
    Reject requests that need a Celery worker when CELERY_ENABLED is False.
    """

    if not settings.CELERY_ENABLED:
        raise NotImplementedHttpError(ORCHESTRATION_DISABLED_MESSAGE)
