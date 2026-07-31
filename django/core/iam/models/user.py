from typing import TYPE_CHECKING

from allauth.account.models import EmailAddress
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.conf import settings

from ..permissions.mixins import ResourcePermissionMixin

if TYPE_CHECKING:
    from .workspace import Workspace
    from .collaborator import Collaborator


class UserQuerySet(models.QuerySet):
    def delete(self):
        from .workspace import Workspace

        Workspace.objects.filter(owner__in=self).delete()

        return super().delete()


class UserManager(BaseUserManager.from_queryset(UserQuerySet)):
    model: "User"
    use_in_migrations = True

    def get_queryset(self):
        return super().get_queryset().select_related("organization")

    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")

        email = self.normalize_email(email)
        user = self.model(username=email, email=email, **extra_fields)

        if user.is_superuser:
            user.owned_workspace_limit = None
        elif not settings.ACCOUNT_OWNERSHIP_ENABLED:
            user.owned_workspace_limit = 0

        user.set_password(password)
        user.save(using=self._db)  # noqa

        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", "Admin")

        user = self.create_user(email, password, **extra_fields)

        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)

        return user


class User(AbstractUser, ResourcePermissionMixin):
    email = models.EmailField(unique=True)
    middle_name = models.CharField(max_length=30, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    link = models.URLField(max_length=2000, blank=True, null=True)
    user_type = models.CharField(max_length=255)
    organization = models.OneToOneField(
        "Organization",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="user",
    )
    owned_workspace_limit = models.PositiveSmallIntegerField(
        default=1, blank=True, null=True
    )

    owned_workspaces: models.QuerySet["Workspace"]
    collaborations: models.QuerySet["Collaborator"]

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def __str__(self):
        return self.email

    def delete(self, *args, **kwargs):
        return type(self).objects.filter(pk=self.pk).delete()  # noqa

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def organization_name(self):
        return self.organization.name if self.organization else None

    @property
    def account_type(self):
        if self.is_superuser:
            return "admin"
        if self.owned_workspace_limit == 0:
            return "limited"
        return "standard"

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)


class UserType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    public = models.BooleanField(default=True)

    def __str__(self):
        return self.name
