import uuid6
import secrets
import string
from typing import Literal, Optional, TYPE_CHECKING
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from .workspace import Workspace
from .utils import PermissionChecker

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


class APIKeyQueryset(models.QuerySet):
    def visible(self, principal: Optional["User"]):
        if principal is None:
            return self.none()
        elif hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return self
            else:
                return self.filter(
                    Q(workspace__owner=principal)
                    | Q(
                        workspace__collaborators__user=principal,
                        workspace__collaborators__role__permissions__resource_type__in=[
                            "*",
                            "APIKey",
                        ],
                        workspace__collaborators__role__permissions__permission_type__in=[
                            "*",
                            "view",
                        ],
                    )
                )
        else:
            return self.none()


class APIKeyManager(models.Manager.from_queryset(APIKeyQueryset)):
    def create_with_key(self, **kwargs):
        prefix = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(12)
        )
        secret = secrets.token_urlsafe(32)
        raw_key = f"{prefix}{secret}"
        hashed_key = f"{prefix}${make_password(raw_key)}"
        kwargs["hashed_key"] = hashed_key

        obj = self.model(**kwargs)
        obj.save()

        return obj, raw_key


class APIKey(models.Model, PermissionChecker):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    workspace = models.ForeignKey(
        "Workspace", on_delete=models.DO_NOTHING, related_name="apikeys"
    )
    role = models.ForeignKey(
        "Role", on_delete=models.DO_NOTHING, related_name="apikeys"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    hashed_key = models.CharField(max_length=128, editable=False)

    objects = APIKeyManager()

    def __str__(self):
        return f"{self.name} - {self.id}"

    def generate_key(self):
        prefix = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(12)
        )
        secret = secrets.token_urlsafe(32)
        raw_key = f"{prefix}{secret}"
        self.hashed_key = f"{prefix}${make_password(raw_key)}"
        self.save(update_fields=["hashed_key"])

        return raw_key

    @classmethod
    def can_principal_create(cls, principal: Optional["User"], workspace: Workspace):
        return cls.check_create_permissions(
            principal=principal, workspace=workspace, resource_type="APIKey"
        )

    def get_principal_permissions(
        self, principal: Optional["User"]
    ) -> list[Literal["edit", "delete", "view"]]:
        permissions = self.check_object_permissions(
            principal=principal, workspace=self.workspace, resource_type="APIKey"
        )

        return permissions

    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
