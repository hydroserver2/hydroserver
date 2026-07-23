from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.hashers import check_password
from ninja.security import APIKeyHeader


class APIKeyAuth(APIKeyHeader):
    param_name = "X-Api-Key"

    def authenticate(self, request, key):
        from core.iam.models import ServiceAccount

        if not key or len(key) < 12:
            return None

        key_prefix = key[:12]
        now = timezone.now()

        service_account_match = ServiceAccount.objects.filter(
            is_active=True, key_prefix=key_prefix
        ).filter(Q(key_expires_at__isnull=True) | Q(key_expires_at__gt=now))

        for service_account in service_account_match:
            if check_password(key, service_account.key_hash):
                service_account.last_used_at = now
                service_account.save(update_fields=["last_used_at"])
                request.principal = service_account
                return service_account
