import uuid6
from typing import Union, Literal

from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model

from core.iam.models import Workspace, APIKey
from core.iam.models.utils import PermissionChecker
from core.sta.models import Thing


User = get_user_model()


class RatingCurveQuerySet(models.QuerySet):
    def visible(self, principal: Union[User, APIKey]):
        if not principal:
            return self.none()
        elif hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return self
            else:
                return self.filter(
                    Q(thing__workspace__owner=principal)
                    | Q(
                        thing__workspace__collaborators__user=principal,
                        thing__workspace__collaborators__role__permissions__resource_type__in=[
                            "*",
                            "DataProduct",
                        ],
                        thing__workspace__collaborators__role__permissions__permission_type__in=[
                            "*",
                            "view",
                        ],
                    )
                )
        elif hasattr(principal, "workspace"):
            return self.filter(
                Q(
                    thing__workspace__apikeys=principal,
                    thing__workspace__apikeys__role__permissions__resource_type__in=[
                        "*",
                        "DataProduct",
                    ],
                    thing__workspace__apikeys__role__permissions__permission_type__in=[
                        "*",
                        "view",
                    ],
                )
            )
        else:
            return self.none()


class FittingMethod(models.TextChoices):
    LINEAR = "linear"
    POWER_LAW = "power_law"


class RatingCurve(models.Model, PermissionChecker):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    thing = models.ForeignKey(
        Thing,
        on_delete=models.CASCADE,
        related_name="rating_curves",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    fitting_method = models.CharField(max_length=20, choices=FittingMethod)

    objects = RatingCurveQuerySet.as_manager()

    class Meta:
        app_label = "products"

    def __str__(self):
        return f"{self.name} - {self.id}"

    @classmethod
    def can_principal_create(
        cls, principal: Union[User, APIKey, None], workspace: Workspace
    ):
        return cls.check_create_permissions(
            principal=principal, workspace=workspace, resource_type="DataProduct"
        )

    def get_principal_permissions(
        self, principal: Union[User, APIKey, None]
    ) -> list[Literal["edit", "delete", "view"]]:
        return self.check_object_permissions(
            principal=principal, workspace=self.thing.workspace, resource_type="DataProduct"
        )


class RatingCurvePoint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    rating_curve = models.ForeignKey(
        RatingCurve,
        on_delete=models.CASCADE,
        related_name="points",
    )
    input_value = models.FloatField()
    output_value = models.FloatField()

    class Meta:
        app_label = "products"
        ordering = ["input_value"]

    def __str__(self):
        return f"{self.rating_curve}: {self.input_value} -> {self.output_value}"
