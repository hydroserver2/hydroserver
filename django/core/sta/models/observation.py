import io
import math
import uuid
import operator
import orjson

from decimal import Decimal, ROUND_HALF_EVEN
from django.core.exceptions import ValidationError
from django.db import models, connection

from core.iam.permissions.registry import register_resource_type

from .datastream import Datastream, PROFILE_COVERAGE

Z_QUANTUM = Decimal("0.000001")
Z_LIMIT = Decimal(10) ** 8


def normalize_z_values(datastream: Datastream, values) -> list[Decimal | None]:
    """
    Validates the z values of new observations on a datastream and rounds them to the 6 decimal places the z column
    stores, so every write path stores the same input as the same value. Time series observations have no z, and
    profile observations each need a finite z.
    """

    if datastream.type != PROFILE_COVERAGE:
        if any(value is not None for value in values):
            raise ValidationError("z is only allowed on profile coverage datastreams")
        return [None] * len(values)

    normalized = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)) or not math.isfinite(value):
            raise ValidationError("Observations on profile coverage datastreams need a numeric z")
        z = Decimal(str(value))
        if abs(z) < Z_LIMIT:
            z = z.quantize(Z_QUANTUM, rounding=ROUND_HALF_EVEN)
        if abs(z) >= Z_LIMIT:
            raise ValidationError("z must be less than 100000000")
        normalized.append(z)

    return normalized


class ObservationQuerySet(models.QuerySet):
    def bulk_copy(self, observations, batch_size=100_000):
        db_table_sql = connection.ops.quote_name(self.model._meta.db_table)  # noqa
        db_fields = [field.column for field in self.model._meta.fields]
        quoted_fields = [connection.ops.quote_name(field) for field in db_fields]
        db_fields_sql = ", ".join(quoted_fields)

        attr_getters = [operator.attrgetter(field) for field in db_fields]

        def escape_pg_copy(value):
            if value is None:
                return r"\N"
            if isinstance(value, (list, dict)):
                value = orjson.dumps(value).decode()
            if isinstance(value, str):
                return (
                    value.replace("\\", "\\\\")
                    .replace("\t", "\\t")
                    .replace("\n", "\\n")
                    .replace("\r", "\\r")
                )
            return str(value)

        with connection.cursor() as cursor:
            with cursor.copy(
                f"COPY {db_table_sql} ({db_fields_sql}) FROM STDIN"
            ) as copy:
                buffer = io.StringIO()
                for i in range(0, len(observations), batch_size):
                    batch = observations[i : i + batch_size]
                    lines = []
                    for obs in batch:
                        line = "\t".join(
                            escape_pg_copy(
                                getter(obs) if field != "id" else str(obs.id)
                            )
                            for field, getter in zip(db_fields, attr_getters)
                        )
                        lines.append(line)
                    buffer.write("\n".join(lines) + "\n")
                    buffer.seek(0)
                    copy.write(buffer.read())
                    buffer.truncate(0)
                    buffer.seek(0)

        return observations


@register_resource_type(workspace_field="datastream__monitoring_site__workspace", privacy_chain=[
    "datastream__is_private", "datastream__is_restricted",
    "datastream__monitoring_site__is_private",
    "datastream__monitoring_site__workspace__is_private"
])
class Observation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    datastream = models.ForeignKey(Datastream, on_delete=models.DO_NOTHING)
    phenomenon_time = models.DateTimeField()
    z = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    result = models.FloatField()
    result_time = models.DateTimeField(null=True, blank=True)
    quality_code = models.CharField(max_length=255, null=True, blank=True)
    result_qualifiers = models.JSONField(default=list, blank=True)

    objects = ObservationQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["datastream_id", "phenomenon_time", "z"],
                nulls_distinct=False,
                name="unique_datastream_id_phenomenon_time_z",
            )
        ]
