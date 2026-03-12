import uuid6
import typing
from typing import Optional, Union
from django.db import models
from django.db.models import Q
from domains.iam.models.utils import PermissionChecker
from .thing import Thing

if typing.TYPE_CHECKING:
    from django.contrib.auth import get_user_model
    from domains.iam.models import APIKey

    User = get_user_model()


class LocationQuerySet(models.QuerySet):
    def visible(self, principal: Optional[Union["User", "APIKey"]]):
        if hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return self
            else:
                return self.filter(
                    Q(thing__workspace__is_private=False, thing__is_private=False)
                    | Q(thing__workspace__owner=principal)
                    | Q(
                        thing__workspace__collaborators__user=principal,
                        thing__workspace__collaborators__role__permissions__resource_type__in=[
                            "*",
                            "Thing",
                        ],
                        thing__workspace__collaborators__role__permissions__permission_type__in=[
                            "*",
                            "view",
                        ],
                    )
                )
        elif hasattr(principal, "workspace"):
            return self.filter(
                Q(thing__workspace__is_private=False, thing__is_private=False)
                | Q(
                    thing__workspace__apikeys=principal,
                    thing__workspace__apikeys__role__permissions__resource_type__in=[
                        "*",
                        "Thing",
                    ],
                    thing__workspace__apikeys__role__permissions__permission_type__in=[
                        "*",
                        "view",
                    ],
                )
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
