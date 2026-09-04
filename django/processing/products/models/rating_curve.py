import uuid

from django.db import models

from core.iam.permissions.mixins import ResourcePermissionMixin
from core.iam.permissions.registry import register_resource_type
from core.sta.models import MonitoringSite


class FittingMethod(models.TextChoices):
    LINEAR = "linear"
    POWER_LAW = "power_law"


@register_resource_type(workspace_field="monitoring_site__workspace")
class RatingCurve(models.Model, ResourcePermissionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    monitoring_site = models.ForeignKey(
        MonitoringSite,
        on_delete=models.CASCADE,
        related_name="rating_curves",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    fitting_method = models.CharField(max_length=20, choices=FittingMethod)

    class Meta:
        app_label = "products"

    def __str__(self):
        return f"{self.name} - {self.id}"


class RatingCurvePoint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
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
        constraints = [
            models.UniqueConstraint(
                fields=["rating_curve", "input_value"],
                name="unique_rating_curve_point_input_value",
                violation_error_message="A point with this input_value already exists on this rating curve.",
            )
        ]

    def __str__(self):
        return f"{self.rating_curve}: {self.input_value} -> {self.output_value}"
