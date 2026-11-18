"""
Add profile coverage datastreams.

Profile coverage datastreams hold observations at a vertical offset z from a datum (z_reference), measured in
z_unit, so one datastream can hold several observations at the same phenomenon time. Every existing datastream is a
time series coverage with null z fields, so no data changes are needed. The observation unique constraint gains z in
0012, which builds its index without blocking writes.
"""

import django.contrib.postgres.indexes
import django.contrib.postgres.search
import django.db.models.deletion
import uuid
from django.db import migrations, models


ZREFERENCE_SEARCH_VECTOR_SQL = """
    CREATE OR REPLACE FUNCTION sta_zreference_search_vector_trigger() RETURNS trigger AS $$
    BEGIN
        NEW.search_vector :=
            setweight(to_tsvector('english', coalesce(NEW.description, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(NEW.name, '')), 'C');
        RETURN NEW;
    END
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER sta_zreference_search_vector_ins_trg
    BEFORE INSERT ON sta_zreference
    FOR EACH ROW EXECUTE FUNCTION sta_zreference_search_vector_trigger();

    CREATE TRIGGER sta_zreference_search_vector_upd_trg
    BEFORE UPDATE ON sta_zreference
    FOR EACH ROW WHEN (OLD.description IS DISTINCT FROM NEW.description OR OLD.name IS DISTINCT FROM NEW.name)
    EXECUTE FUNCTION sta_zreference_search_vector_trigger();
"""

ZREFERENCE_SEARCH_VECTOR_REVERSE_SQL = """
    DROP TRIGGER IF EXISTS sta_zreference_search_vector_upd_trg ON sta_zreference;
    DROP TRIGGER IF EXISTS sta_zreference_search_vector_ins_trg ON sta_zreference;
    DROP FUNCTION IF EXISTS sta_zreference_search_vector_trigger();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("sta", "0010_datastream_is_restricted"),
    ]

    operations = [
        # --- Z reference vocabulary -----------------------------------------------------
        migrations.CreateModel(
            name="ZReference",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid7, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                ("search_vector", django.contrib.postgres.search.SearchVectorField(editable=False, null=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="zreference",
            constraint=models.UniqueConstraint(fields=("name",), name="unique_z_reference_name"),
        ),
        migrations.AddIndex(
            model_name="zreference",
            index=django.contrib.postgres.indexes.GinIndex(fields=["search_vector"], name="sta_zref_search_gin"),
        ),
        migrations.RunSQL(sql=ZREFERENCE_SEARCH_VECTOR_SQL, reverse_sql=ZREFERENCE_SEARCH_VECTOR_REVERSE_SQL),

        # --- Datastream ------------------------------------------------------------------
        migrations.AlterField(
            model_name="datastream",
            name="type",
            field=models.CharField(
                choices=[("timeSeriesCoverage", "Time Series Coverage"), ("profileCoverage", "Profile Coverage")],
                default="timeSeriesCoverage",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="datastream",
            name="z_reference",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="datastream",
            name="z_unit",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="z_datastreams",
                to="sta.unit",
            ),
        ),
        migrations.AddField(
            model_name="datastream",
            name="z_min",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name="datastream",
            name="z_max",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True),
        ),
        migrations.AddConstraint(
            model_name="datastream",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("type", "timeSeriesCoverage"), ("z_reference__isnull", True), ("z_unit__isnull", True)),
                    models.Q(("type", "profileCoverage"), ("z_reference__isnull", False), ("z_unit__isnull", False)),
                    _connector="OR",
                ),
                name="datastream_type_z_fields",
            ),
        ),

        # --- Observation -----------------------------------------------------------------
        migrations.AddField(
            model_name="observation",
            name="z",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True),
        ),
    ]
