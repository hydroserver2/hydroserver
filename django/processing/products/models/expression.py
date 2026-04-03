import uuid6
from typing import Union, Literal

from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model

from core.iam.models import Workspace, APIKey
from core.iam.models.utils import PermissionChecker
from core.sta.models import Thing


User = get_user_model()


class ExpressionQuerySet(models.QuerySet):
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
                            "DataProducts",
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
                        "DataProducts",
                    ],
                    thing__workspace__apikeys__role__permissions__permission_type__in=[
                        "*",
                        "view",
                    ],
                )
            )
        else:
            return self.none()


class Expression(models.Model, PermissionChecker):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    thing = models.ForeignKey(
        Thing,
        on_delete=models.CASCADE,
        related_name="expressions",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    breakpoint_variable = models.CharField(max_length=255, null=True, blank=True)

    objects = ExpressionQuerySet.as_manager()

    class Meta:
        app_label = "products"

    def __str__(self):
        return f"{self.name} - {self.id}"

    @classmethod
    def can_principal_create(
        cls, principal: Union[User, APIKey, None], workspace: Workspace
    ):
        return cls.check_create_permissions(
            principal=principal, workspace=workspace, resource_type="DataProducts"
        )

    def get_principal_permissions(
        self, principal: Union[User, APIKey, None]
    ) -> list[Literal["edit", "delete", "view"]]:
        return self.check_object_permissions(
            principal=principal, workspace=self.thing.workspace, resource_type="DataProducts"
        )


class ExpressionSegment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    expression = models.ForeignKey(
        Expression,
        on_delete=models.CASCADE,
        related_name="segments",
    )
    lower_bound = models.FloatField(null=True, blank=True)
    upper_bound = models.FloatField(null=True, blank=True)
    formula = models.TextField(null=True, blank=True)

    class Meta:
        app_label = "products"

    def __str__(self):
        return f"{self.expression} [{self.lower_bound}, {self.upper_bound}]"
