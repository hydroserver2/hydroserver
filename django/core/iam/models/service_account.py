import uuid
import secrets
import string

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password

from ..permissions.registry import register_resource_type
from ..permissions.mixins import ResourcePermissionMixin
from .workspace import Workspace


@register_resource_type()
class ServiceAccount(models.Model, ResourcePermissionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    email = models.EmailField(unique=True, blank=True, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="service_accounts",
    )
    created_at = models.DateTimeField(default=timezone.now)
    last_used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    key_prefix = models.CharField(max_length=12, unique=True, editable=False)
    key_hash = models.CharField(max_length=128, blank=True, editable=False)
    key_created_at = models.DateTimeField(null=True, blank=True, editable=False)
    key_expires_at = models.DateTimeField(null=True, blank=True)

    is_authenticated = True

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if self._state.adding and not self.key_hash:
            self.generate_key()
        if not self.email:
            self.email = f"{self.key_prefix}@service-accounts.{settings.SERVICE_ACCOUNT_EMAIL_DOMAIN}"

        super().save(*args, **kwargs)

    def generate_key(self):
        key_prefix = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(12)
        )
        key_secret = secrets.token_urlsafe(32)
        raw_key = f"{key_prefix}{key_secret}"

        self.key_prefix = key_prefix
        self.key_hash = make_password(raw_key)
        self.key_created_at = timezone.now()

        if not self._state.adding:
            self.save(update_fields=["key_prefix", "key_hash", "key_created_at"])

        return raw_key

    def deactivate(self):
        self.is_active = False
        self.key_hash = ""
        self.deactivated_at = timezone.now()

        self.save(
            update_fields=["is_active", "deactivated_at", "key_hash"]
        )

    class Meta:
        verbose_name = "Service Account"
        verbose_name_plural = "Service Accounts"
