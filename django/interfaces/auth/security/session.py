from typing import Any
from ninja.security.apikey import APIKeyCookie
from ninja.utils import check_csrf
from django.http import HttpRequest
from django.conf import settings
from interfaces.api.http.errors import PermissionDeniedError
from interfaces.auth.security.credentials import has_credential_header


class SessionAuth(APIKeyCookie):
    param_name: str = settings.SESSION_COOKIE_NAME

    def authenticate(self, request: HttpRequest, key: str) -> Any:
        if not key or not request.user.is_authenticated:
            return None

        if self._csrf_required(request) and check_csrf(request) is not None:
            if has_credential_header(request):
                return None
            raise PermissionDeniedError("CSRF check failed")

        request.principal = request.user

        return request.user

    def _csrf_required(self, request: HttpRequest) -> bool:
        return (
            settings.STRICT_SECURITY
            and self.csrf
            and not getattr(request, "_ninja_csrf_exempt", False)
        )

    def _get_key(self, request: HttpRequest) -> Any:
        return request.COOKIES.get(self.param_name)
