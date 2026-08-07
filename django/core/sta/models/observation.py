import io
import uuid
import operator
import orjson

from django.db import models, connection

from core.iam.permissions.registry import register_resource_type

from .datastream import Datastream


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
    "datastream__is_private", "datastream__monitoring_site__is_private",
    "datastream__monitoring_site__workspace__is_private"
])
class Observation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    datastream = models.ForeignKey(Datastream, on_delete=models.DO_NOTHING)
    phenomenon_time = models.DateTimeField()
    result = models.FloatField()
    result_time = models.DateTimeField(null=True, blank=True)
    quality_code = models.CharField(max_length=255, null=True, blank=True)
    result_qualifiers = models.JSONField(default=list, blank=True)

    objects = ObservationQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["datastream_id", "phenomenon_time"],
                name="unique_datastream_id_phenomenon_time",
            )
        ]
