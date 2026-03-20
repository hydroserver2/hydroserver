from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.hashers import check_password
from ninja.security import APIKeyHeader
from domains.iam.models import APIKey


class APIKeyAuth(APIKeyHeader):
    param_name = "X-Api-Key"

    def authenticate(self, request, key):
        if not key or len(key) < 12:
            return None

        short_id = key[:12]
        now = timezone.now()

        api_key_match = APIKey.objects.filter(
            is_active=True, hashed_key__startswith=short_id + "$"
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))

        for api_key in api_key_match:
            if check_password(key, api_key.hashed_key.split("$", 1)[1]):
                api_key.last_used_at = now
                api_key.save(update_fields=["last_used"])
                request.principal = api_key
                return api_key
