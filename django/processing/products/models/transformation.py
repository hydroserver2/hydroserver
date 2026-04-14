import uuid6

from django.db import models

from core.sta.models import Datastream
from processing.products.models.task import DataProductTask


class TransformationType(models.TextChoices):
    RATING_CURVE = "rating_curve"
    EXPRESSION = "expression"
    COMPOSITE_EXPRESSION = "composite_expression"
    AGGREGATION = "aggregation"


class AggregationMethod(models.TextChoices):
    SIMPLE_MEAN = "simple_mean"
    SUM = "sum"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    FIRST_VALUE = "first_value"
    LAST_VALUE = "last_value"


class IntervalUnits(models.TextChoices):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"


class TimezoneType(models.TextChoices):
    UTC = "utc"
    OFFSET = "offset"
    IANA = "iana"


class DataProductTransformation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    task = models.ForeignKey(
        DataProductTask,
        on_delete=models.CASCADE,
        related_name="transformations",
    )
    output_datastream = models.OneToOneField(
        Datastream,
        on_delete=models.CASCADE,
        related_name="data_product_transformation",
    )
    transformation_type = models.CharField(max_length=255, choices=TransformationType)
    rating_curve = models.ForeignKey(
        "products.RatingCurve",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="transformations",
    )
    formula = models.TextField(null=True, blank=True)
    output_interval_units = models.CharField(max_length=255, choices=IntervalUnits, null=True, blank=True)
    output_interval = models.PositiveIntegerField(null=True, blank=True)
    timezone_type = models.CharField(max_length=255, choices=TimezoneType, null=True, blank=True)
    timezone = models.CharField(max_length=255, null=True, blank=True)
    aggregation_method = models.CharField(
        max_length=255,
        choices=AggregationMethod,
        null=True,
        blank=True,
    )
    max_gap_interval_units = models.CharField(max_length=255, choices=IntervalUnits, null=True, blank=True)
    max_gap_interval = models.PositiveIntegerField(null=True, blank=True)
    min_values = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        app_label = "products"

    def __str__(self):
        return f"{self.task} - {self.output_datastream} ({self.transformation_type})"


class DataProductTransformationInput(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    transformation = models.ForeignKey(
        DataProductTransformation,
        on_delete=models.CASCADE,
        related_name="input_datastreams",
    )
    datastream = models.ForeignKey(
        Datastream,
        on_delete=models.CASCADE,
        related_name="data_product_transformation_inputs",
    )
    variable_name = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        app_label = "products"
        constraints = [
            models.UniqueConstraint(
                fields=["transformation", "variable_name"],
                condition=models.Q(variable_name__isnull=False),
                name="unique_data_product_transformation_input_variable",
            ),
        ]

    def __str__(self):
        return f"{self.transformation} <- {self.datastream} ({self.variable_name})"
