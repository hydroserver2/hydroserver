import ast
import re
import uuid

import pytz

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models

from core.sta.models import Datastream
from processing.products.models.task import DataProductTask


ALLOWED_NODE_TYPES = frozenset({
    ast.Expression,
    ast.BinOp,
    ast.Add, ast.Sub, ast.Mult, ast.Div,
    ast.UnaryOp, ast.UAdd, ast.USub,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Call,
})

ALLOWED_FUNCTIONS = frozenset({
    "abs", "min", "max",
    "sqrt", "log", "log10", "log2", "exp",
    "sin", "cos", "tan", "asin", "acos", "atan",
    "floor", "ceil",
})

TZ_OFFSET_RE = re.compile(r"^([+-])(\d{2}):?(\d{2})$")
TZ_SIGN_FLIP = {"+": "-", "-": "+"}


def _validate_derivation_formula(formula: str, variables: list[str]) -> None:
    """
    Validate a formula string against the approved AST whitelist and variable names.

    Native port of hydroserverpy.products.derivation.validate_derivation_formula -
    kept in sync manually since models must not import hydroserverpy.

    Raises ValueError if:
      - Any variable name conflicts with an approved function name.
      - The formula fails to parse as a Python expression.
      - The formula contains any disallowed AST node type.
      - The formula contains a non-numeric or boolean literal.
      - The formula references a name not in variables or approved functions.
      - The formula calls a function not in the approved functions list.
    """

    if conflicts := set(variables) & ALLOWED_FUNCTIONS:
        raise ValueError(
            f"Variable names conflict with derivation functions: {sorted(conflicts)}."
        )

    try:
        tree = ast.parse(formula.strip(), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Formula syntax error: {e}") from e

    allowed_names = set(variables) | ALLOWED_FUNCTIONS

    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODE_TYPES:
            raise ValueError(
                f"Formula contains a disallowed construct: {type(node).__name__!r}."
            )
        if isinstance(node, ast.Constant) and (
            isinstance(node.value, bool) or not isinstance(node.value, (int, float))
        ):
            raise ValueError(
                f"Formula contains a disallowed literal {node.value!r}. "
                "Only numeric literals are permitted."
            )
        if isinstance(node, ast.Name) and node.id not in allowed_names:
            raise ValueError(
                f"Formula references unknown name '{node.id}'. "
                f"Known variables: {sorted(variables)}. "
                f"Approved functions: {sorted(ALLOWED_FUNCTIONS)}."
            )
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCTIONS:
                raise ValueError(
                    f"Formula calls unsupported function '{ast.unparse(node.func)}'. "
                    f"Approved functions: {sorted(ALLOWED_FUNCTIONS)}."
                )


def _normalize_tz(tz: str) -> str:
    """
    Normalize a timezone string to a pandas and zoneinfo compatible IANA name.

    Native port of hydroserverpy.core.timeseries.normalize_tz - kept in sync
    manually since models must not import hydroserverpy.

    Accepts any of the following:
      - IANA timezone names (e.g. 'America/Denver', 'UTC')
      - Etc/GMT offset names (e.g. 'Etc/GMT+5', 'Etc/GMT-7')
      - UTC offset strings in ±HHMM or ±HH:MM format (e.g. '+0500', '-07:00')

    UTC offset strings are converted to Etc/GMT±H names. Note that Etc/GMT sign
    convention is the reverse of the UTC offset sign (POSIX legacy):
      '+05:00' (UTC+5) → 'Etc/GMT-5'
      '-07:00' (UTC-7) → 'Etc/GMT+7'

    Only whole-hour offsets are supported via the offset format. For non-whole-hour
    offsets (e.g., UTC+5:30), use the IANA name directly (e.g. 'Asia/Kolkata').

    Raises ValueError for unrecognized or invalid input.
    """

    offset_match = TZ_OFFSET_RE.fullmatch(tz)

    if offset_match:
        sign, hours, minutes = offset_match.group(1), int(offset_match.group(2)), int(offset_match.group(3))

        if minutes != 0:
            raise ValueError(
                f"UTC offset '{tz}' has a non-zero minute component. "
                "Use an IANA timezone name for non-whole-hour offsets "
                "(e.g. 'Asia/Kolkata' for UTC+5:30)."
            )
        if hours > 14:
            raise ValueError(
                f"UTC offset '{tz}' is out of the valid range (±14:00)."
            )
        if hours == 0:
            return "UTC"

        # Etc/GMT sign is opposite to the UTC offset sign (POSIX convention)
        return f"Etc/GMT{TZ_SIGN_FLIP[sign]}{hours}"

    if tz not in pytz.all_timezones_set:
        raise ValueError(
            f"Unknown timezone '{tz}'. "
            "Provide a valid IANA timezone name (e.g. 'America/Denver') "
            "or a UTC offset in ±HHMM or ±HH:MM format (e.g. '-0700' or '-07:00')."
        )

    return tz


class TransformationType(models.TextChoices):
    RATING_CURVE = "rating_curve"
    DERIVATION = "derivation"
    AGGREGATION = "aggregation"


class AggregationMethod(models.TextChoices):
    MEAN = "mean"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    FIRST = "first"
    LAST = "last"
    TIME_WEIGHTED_MEAN = "time_weighted_mean"


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
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
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
    min_values = models.PositiveIntegerField(null=True, blank=True)
    stop_on_no_data = models.BooleanField(default=True, blank=True)
    stop_on_error = models.BooleanField(default=True, blank=True)

    class Meta:
        app_label = "products"

    def __str__(self):
        return f"{self.task} - {self.output_datastream} ({self.transformation_type})"

    def clean(self):
        if not self.output_datastream_id or not self.task_id:
            return
        try:
            output_workspace_id = self.output_datastream.monitoring_site.workspace_id
            output_site_id = self.output_datastream.monitoring_site_id
        except ObjectDoesNotExist:
            return
        try:
            task_workspace_id = self.task.monitoring_site.workspace_id
            task_site_id = self.task.monitoring_site_id
        except ObjectDoesNotExist:
            return

        if output_workspace_id != task_workspace_id:
            raise ValidationError("The output datastream must belong to the same workspace as this task.")
        if output_site_id != task_site_id:
            raise ValidationError("The output datastream must belong to the same monitoring site as this task.")

        if self.transformation_type == TransformationType.RATING_CURVE:
            if not self.rating_curve_id:
                raise ValidationError("rating_curve is required for transformation_type 'rating_curve'.")
            if any([self.formula, self.output_interval_units, self.output_interval is not None,
                    self.aggregation_method, self.min_values is not None]):
                raise ValidationError(
                    "formula, output_interval_units, output_interval, aggregation_method, and min_values "
                    "must not be set for transformation_type 'rating_curve'."
                )
            try:
                if self.rating_curve.monitoring_site_id != task_site_id:
                    raise ValidationError("The rating curve must belong to the same monitoring site as this task.")
            except ObjectDoesNotExist:
                pass

        elif self.transformation_type == TransformationType.DERIVATION:
            if not self.formula:
                raise ValidationError("formula is required for transformation_type 'derivation'.")
            if any([self.rating_curve_id, self.output_interval_units, self.output_interval is not None,
                    self.aggregation_method, self.min_values is not None]):
                raise ValidationError(
                    "rating_curve, output_interval_units, output_interval, aggregation_method, and min_values "
                    "must not be set for transformation_type 'derivation'."
                )
            if not self.input_datastreams.exists():
                raise ValidationError(
                    "At least one input datastream is required for transformation_type 'derivation'."
                )
            variable_names = [i.variable_name for i in self.input_datastreams.all() if i.variable_name]

            try:
                _validate_derivation_formula(self.formula, variable_names)
            except ValueError as e:
                raise ValidationError(str(e)) from e

        elif self.transformation_type == TransformationType.AGGREGATION:
            if not all([self.aggregation_method, self.output_interval_units, self.output_interval is not None]):
                raise ValidationError(
                    "aggregation_method, output_interval_units, and output_interval are required for "
                    "transformation_type 'aggregation'."
                )
            if any([self.rating_curve_id, self.formula]):
                raise ValidationError(
                    "rating_curve and formula must not be set for transformation_type 'aggregation'."
                )
            if self.timezone and not self.timezone_type:
                raise ValidationError("timezone_type is required when timezone is set.")
            if self.timezone_type == TimezoneType.UTC and self.timezone:
                raise ValidationError("timezone must not be set when timezone_type is 'utc'.")
            if self.timezone_type in (TimezoneType.IANA, TimezoneType.OFFSET):
                if not self.timezone:
                    raise ValidationError(f"timezone is required when timezone_type is '{self.timezone_type}'.")
                try:
                    _normalize_tz(self.timezone)
                except ValueError as e:
                    raise ValidationError(str(e)) from e


class DataProductTransformationInput(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
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

    def clean(self):
        if not self.datastream_id or not self.transformation_id:
            return
        try:
            datastream_workspace_id = self.datastream.monitoring_site.workspace_id
        except ObjectDoesNotExist:
            return
        try:
            task_workspace_id = self.transformation.task.monitoring_site.workspace_id
        except ObjectDoesNotExist:
            return
        if datastream_workspace_id != task_workspace_id:
            raise ValidationError("The input datastream must belong to the same workspace as this task.")
        if (
            self.transformation.transformation_type == TransformationType.DERIVATION
            and not self.variable_name
        ):
            raise ValidationError(
                "variable_name is required for every input of transformation_type 'derivation'."
            )

    def __str__(self):
        return f"{self.transformation} <- {self.datastream} ({self.variable_name})"
