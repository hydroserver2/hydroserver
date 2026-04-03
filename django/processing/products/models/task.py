import uuid6
from typing import Union, Literal

from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model

from core.iam.models import Workspace, APIKey
from core.iam.models.utils import PermissionChecker
from core.sta.models import Thing, Datastream
from processing.orchestration.models.task import Task


User = get_user_model()


class DataProductTaskQuerySet(models.QuerySet):
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


class TimezoneType(models.TextChoices):
    UTC = "utc"
    OFFSET = "offset"
    IANA = "iana"


class TransformationType(models.TextChoices):
    RATING_CURVE = "rating_curve"
    EXPRESSION = "expression"
    TEMPORAL_AGGREGATION = "temporal_aggregation"


class AggregationMethod(models.TextChoices):
    SIMPLE_MEAN = "simple_mean"
    WEIGHTED_MEAN = "weighted_mean"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    FIRST_VALUE = "first_value"
    LAST_VALUE = "last_value"


class AggregationPeriod(models.TextChoices):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DataProductTask(Task, PermissionChecker):
    thing = models.ForeignKey(
        Thing,
        on_delete=models.CASCADE,
        related_name="data_product_tasks",
    )

    objects = DataProductTaskQuerySet.as_manager()

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

    @property
    def workspace(self):
        return self.thing.workspace


class DataProductOutputMapping(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    task = models.ForeignKey(
        DataProductTask,
        on_delete=models.CASCADE,
        related_name="mappings",
    )
    output_datastream = models.OneToOneField(
        Datastream,
        on_delete=models.CASCADE,
        related_name="data_product_mapping",
    )
    transformation_type = models.CharField(max_length=255, choices=TransformationType)
    rating_curve = models.ForeignKey(
        "products.RatingCurve",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="mappings",
    )
    expression = models.ForeignKey(
        "products.Expression",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="mappings",
    )
    aggregation_method = models.CharField(
        max_length=255,
        choices=AggregationMethod,
        null=True,
        blank=True,
    )
    aggregation_period = models.CharField(
        max_length=255,
        choices=AggregationPeriod,
        null=True,
        blank=True,
    )
    aggregation_timezone_type = models.CharField(max_length=255, choices=TimezoneType, null=True, blank=True)
    aggregation_timezone = models.CharField(max_length=255, null=True, blank=True)
    aggregation_min_coverage = models.FloatField(null=True, blank=True)

    class Meta:
        app_label = "products"

    def __str__(self):
        return f"{self.task} - {self.output_datastream} ({self.transformation_type})"


class DataProductInputMapping(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    output_mapping = models.ForeignKey(
        DataProductOutputMapping,
        on_delete=models.CASCADE,
        related_name="input_mappings",
    )
    datastream = models.ForeignKey(
        Datastream,
        on_delete=models.CASCADE,
        related_name="data_product_input_mappings",
    )
    variable_name = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        app_label = "products"
        constraints = [
            models.UniqueConstraint(
                fields=["output_mapping", "variable_name"],
                condition=models.Q(variable_name__isnull=False),
                name="unique_data_product_input_mapping_variable",
            )
        ]

    def __str__(self):
        return f"{self.output_mapping} <- {self.datastream} ({self.variable_name})"
