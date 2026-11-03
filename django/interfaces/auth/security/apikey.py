from django.utils import timezone
from django.contrib.auth.hashers import check_password
from ninja.security import APIKeyHeader
from core.iam.models import ServiceAccount
from interfaces.api.http.errors import UnauthorizedError


class APIKeyAuth(APIKeyHeader):
    param_name = "X-Api-Key"

    def authenticate(self, request, key):
        if not key:
            return None

        if len(key) < 12:
            raise UnauthorizedError("Invalid API key")

        service_account = ServiceAccount.objects.filter(key_prefix=key[:12]).first()

        if (
            service_account is None
            or not service_account.is_active
            or not check_password(key, service_account.key_hash)
        ):
            raise UnauthorizedError("Invalid API key")

        now = timezone.now()

        if service_account.key_expires_at is not None and service_account.key_expires_at <= now:
            raise UnauthorizedError("API key has expired")

        service_account.last_used_at = now
        service_account.save(update_fields=["last_used_at"])
        request.principal = service_account

        return service_account
