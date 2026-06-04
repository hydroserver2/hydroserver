import uuid6
import typing
from typing import Optional, Union
from django.db import models
from django.db.models import Q, OuterRef, Exists
from core.iam.models import Collaborator, APIKey as _APIKey
from core.iam.models.utils import PermissionChecker
from .thing import Thing

if typing.TYPE_CHECKING:
    from django.contrib.auth import get_user_model
    from core.iam.models import APIKey

    User = get_user_model()


class LocationQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        from core.sta.cache import invalidate_public_thing_markers_cache

        invalidate_public_thing_markers_cache()
        return super().delete(*args, **kwargs)

    def visible(self, principal: Optional[Union["User", "APIKey"]]):
        if hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return self
            else:
                collaborator_subquery = Collaborator.objects.filter(
                    workspace=OuterRef("thing__workspace"),
                    user=principal,
                    role__permissions__resource_type__in=["*", "Thing"],
                    role__permissions__permission_type__in=["*", "view"],
                )
                return self.filter(
                    Q(thing__workspace__is_private=False, thing__is_private=False)
                    | Q(thing__workspace__owner=principal)
                    | Exists(collaborator_subquery)
                )
        elif hasattr(principal, "workspace"):
            apikey_subquery = _APIKey.objects.filter(
                workspace=OuterRef("thing__workspace"),
                id=principal.id,
                role__permissions__resource_type__in=["*", "Thing"],
                role__permissions__permission_type__in=["*", "view"],
            )
            return self.filter(
                Q(thing__workspace__is_private=False, thing__is_private=False)
                | Exists(apikey_subquery)
            )
        else:
            return self.filter(
                Q(thing__workspace__is_private=False, thing__is_private=False)
            )


class Location(models.Model, PermissionChecker):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    thing = models.ForeignKey(
        Thing, related_name="locations", on_delete=models.DO_NOTHING
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    encoding_type = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=22, decimal_places=16)
    longitude = models.DecimalField(max_digits=22, decimal_places=16)
    elevation_m = models.DecimalField(
        max_digits=22, decimal_places=16, null=True, blank=True
    )
    elevation_datum = models.CharField(max_length=255, null=True, blank=True)
    admin_area_1 = models.CharField(max_length=200, null=True, blank=True)
    admin_area_2 = models.CharField(max_length=200, null=True, blank=True)
    country = models.CharField(max_length=2, null=True, blank=True)

    objects = LocationQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} - {self.id}"

    def delete(self, *args, **kwargs):
        from core.sta.cache import invalidate_public_thing_markers_cache

        invalidate_public_thing_markers_cache()
        return super().delete(*args, **kwargs)
