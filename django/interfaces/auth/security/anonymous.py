import logging

from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import UnauthorizedError
from interfaces.auth.security.credentials import CREDENTIAL_HEADERS, has_credential_header

logger = logging.getLogger(__name__)


def anonymous_auth(request):
    if has_credential_header(request):
        sent = [header for header in CREDENTIAL_HEADERS if request.headers.get(header)]
        logger.warning("Rejected unauthenticated credentials in headers: %s", ", ".join(sent))
        raise UnauthorizedError("Invalid or unsupported credentials")

    request.principal = AnonymousPrincipal()

    return True
