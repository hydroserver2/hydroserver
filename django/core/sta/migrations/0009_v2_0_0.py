"""
HydroServer v1.12 -> v2.0.0 schema and data migration for the sta app.

This migration is forward-only. Back up the database before applying it. See the
"Migrating from HydroServer v1 to v2" deployment guide for the manual data fixes this
migration requires and the data it drops or transforms.
"""

import uuid

import core.sta.models.datastream
import core.sta.models.monitoring_site
import core.sta.models.validators
import django.contrib.postgres.indexes
import django.contrib.postgres.search
import django.db.models.deletion
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import migrations, models


def _search_vector_trigger_sql(
    table: str,
    field_weights: dict[str, str],
    vector_column: str = "search_vector",
) -> list[migrations.RunSQL]:
    """
    Builds the migration operations needed to keep a `SearchVectorField` current via a
    Postgres trigger, plus a one-time backfill for existing rows.

    INSERT and UPDATE are handled by separate triggers rather than one combined
    `BEFORE INSERT OR UPDATE` trigger: the UPDATE trigger has a `WHEN` guard comparing
    OLD/NEW on only the source columns, so it skips recomputing the vector when a save
    touches unrelated columns (e.g. observation-statistics updates). INSERT has no OLD
    row to compare against, so it always runs unconditionally.
    """

    function_name = f"{table}_{vector_column}_trigger"
    insert_trigger_name = f"{table}_{vector_column}_ins_trg"
    update_trigger_name = f"{table}_{vector_column}_upd_trg"

    new_expr = " || ".join(
        f"setweight(to_tsvector('english', coalesce(NEW.{field}, '')), '{weight}')"
        for field, weight in field_weights.items()
    )
    backfill_expr = " || ".join(
        f"setweight(to_tsvector('english', coalesce({field}, '')), '{weight}')"
        for field, weight in field_weights.items()
    )
    base_fields = dict.fromkeys(field.split("::", 1)[0] for field in field_weights)
    when_condition = " OR ".join(
        f"OLD.{field} IS DISTINCT FROM NEW.{field}" for field in base_fields
    )

    forward_sql = f"""
        CREATE OR REPLACE FUNCTION {function_name}() RETURNS trigger AS $$
        BEGIN
            NEW.{vector_column} := {new_expr};
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS {insert_trigger_name} ON {table};
        CREATE TRIGGER {insert_trigger_name}
        BEFORE INSERT ON {table}
        FOR EACH ROW EXECUTE FUNCTION {function_name}();

        DROP TRIGGER IF EXISTS {update_trigger_name} ON {table};
        CREATE TRIGGER {update_trigger_name}
        BEFORE UPDATE ON {table}
        FOR EACH ROW WHEN ({when_condition})
        EXECUTE FUNCTION {function_name}();

        UPDATE {table} SET {vector_column} = {backfill_expr};
    """

    return [migrations.RunSQL(sql=forward_sql)]


# (table, model, index name, field weights) for every searchable sta table.
SEARCH_VECTORS = [
    (
        "sta_monitoringsite", "monitoringsite", "sta_monitoringsite_search_gin",
        {"name": "A", "description": "B", "code": "C", "type": "C", "tags::text": "D"},
    ),
    (
        "sta_datastream", "datastream", "sta_datastream_search_gin",
        {
            "name": "A", "description": "B", "observation_type": "C", "result_type": "C",
            "sampled_medium": "C", "status": "C", "tags::text": "D",
        },
    ),
    (
        "sta_observedproperty", "observedproperty", "sta_obsproperty_search_gin",
        {"name": "A", "definition": "B", "description": "B", "type": "C", "code": "C"},
    ),
    (
        "sta_method", "method", "sta_method_search_gin",
        {
            "name": "A", "description": "B", "definition": "B", "type": "C",
            "sensor_model": "C", "sensor_model_manufacturer": "C",
            "sensor_model_definition": "C", "code": "C",
        },
    ),
    (
        "sta_unit", "unit", "sta_unit_search_gin",
        {"name": "A", "definition": "B", "symbol": "C", "type": "C"},
    ),
    (
        "sta_processinglevel", "processinglevel", "sta_proclevel_search_gin",
        {"name": "A", "description": "B", "definition": "B", "code": "C"},
    ),
    (
        "sta_resultqualifier", "resultqualifier", "sta_resultqual_search_gin",
        {"description": "A", "name": "C"},
    ),
    ("sta_sampledmedium", "sampledmedium", "sta_sampledmed_search_gin", {"description": "A", "name": "C"}),
    ("sta_aggregationstatistic", "aggregationstatistic", "sta_aggstat_search_gin", {"description": "A", "name": "C"}),
    ("sta_datastreamstatus", "datastreamstatus", "sta_dsstatus_search_gin", {"description": "A", "name": "C"}),
    ("sta_methodtype", "methodtype", "sta_methodtype_search_gin", {"description": "A", "name": "C"}),
    ("sta_unittype", "unittype", "sta_unittype_search_gin", {"description": "A", "name": "C"}),
    ("sta_observedpropertytype", "observedpropertytype", "sta_optype_search_gin", {"description": "A", "name": "C"}),
    ("sta_monitoringsitetype", "monitoringsitetype", "sta_sitetype_search_gin", {"description": "A", "name": "C"}),
    ("sta_linkedresourcetype", "linkedresourcetype", "sta_linkedrestype_search_gin", {"description": "A", "name": "C"}),
]


def _is_url(value):
    try:
        URLValidator()(value)
    except ValidationError:
        return False
    return True


def check_constraints_immediately(apps, schema_editor):
    """
    The data steps below update rows in tables that are altered later in this same
    transaction. With deferred foreign keys, those updates queue checks until COMMIT,
    and Postgres refuses to ALTER or index a table with pending trigger events. Check
    constraints immediately for the rest of the migration instead.
    """

    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def copy_locations_to_monitoring_sites(apps, schema_editor):
    """
    Merges each site's first Location (by id) into the site. Any additional
    Locations are dropped with the Location table.
    """

    schema_editor.execute("""
        UPDATE sta_monitoringsite AS ms
        SET latitude = l.latitude,
            longitude = l.longitude,
            elevation_m = l.elevation_m,
            elevation_datum = l.elevation_datum,
            admin_area_1 = l.admin_area_1,
            admin_area_2 = l.admin_area_2,
            country = l.country
        FROM (
            SELECT DISTINCT ON (thing_id) *
            FROM sta_location
            ORDER BY thing_id, id
        ) AS l
        WHERE ms.id = l.thing_id
    """)


def copy_tags_to_json(apps, schema_editor):
    """
    Folds tag rows into each site's and datastream's tags object. If a key appears
    more than once, the value of the row with the highest id wins.
    """

    schema_editor.execute("""
        UPDATE sta_monitoringsite
        SET tags = subq.tags
        FROM (
            SELECT thing_id, jsonb_object_agg(key, value ORDER BY id ASC) AS tags
            FROM sta_thingtag
            GROUP BY thing_id
        ) AS subq
        WHERE sta_monitoringsite.id = subq.thing_id
    """)
    schema_editor.execute("""
        UPDATE sta_datastream
        SET tags = subq.tags
        FROM (
            SELECT datastream_id, jsonb_object_agg(key, value ORDER BY id ASC) AS tags
            FROM sta_datastreamtag
            GROUP BY datastream_id
        ) AS subq
        WHERE sta_datastream.id = subq.datastream_id
    """)


def _backfill_uuids(model_name):
    def backfill(apps, schema_editor):
        model = apps.get_model("sta", model_name)
        for row in model.objects.all():
            row.uuid_id = uuid.uuid7()
            row.save(update_fields=["uuid_id"])

    return backfill


def migrate_processing_levels(apps, schema_editor):
    """
    Maps v1 (code, definition, explanation) onto v2 (code, name, definition,
    description):

    - a URL definition stays the definition, and the code becomes the name;
    - a definition of 255 characters or fewer becomes the name;
    - a longer definition is prepended to the description, and the code becomes
      the name.

    The name falls back to the code, then the id, when nothing else is available.
    """

    ProcessingLevel = apps.get_model("sta", "ProcessingLevel")

    for level in ProcessingLevel.objects.all().iterator():
        legacy_definition = (level.definition or "").strip()
        explanation = level.description or ""
        fallback_name = (level.code or "").strip() or str(level.pk)

        if _is_url(legacy_definition):
            level.name = fallback_name
            level.definition = legacy_definition
            level.description = explanation
        elif len(legacy_definition) <= 255:
            level.name = legacy_definition or fallback_name
            level.definition = None
            level.description = explanation
        else:
            level.name = fallback_name
            level.definition = None
            level.description = (
                f"{legacy_definition}\n\n{explanation}" if explanation else legacy_definition
            )

        level.save(update_fields=["name", "definition", "description"])


def _vocabulary_operations(model, table, pkey, unique_name, new_model=None, new_table=None):
    """
    Promotes a v1 name-only lookup table to the v2 vocabulary shape: UUID primary key,
    name/description, and a named unique constraint on name. Search vectors are added
    with the other search vectors at the end of the migration.

    The integer-to-UUID primary key swap is done in raw SQL because it isn't
    expressible as ordinary field operations.
    """

    final_model = new_model or model
    rename_table_sql = f"ALTER TABLE {table} RENAME TO {new_table};" if new_table else ""

    return [
        migrations.AddField(
            model_name=model,
            name="uuid_id",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(_backfill_uuids(model)),
        migrations.AlterField(
            model_name=model,
            name="name",
            field=models.CharField(max_length=255),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(f"""
                    ALTER TABLE {table} DROP CONSTRAINT {pkey};
                    ALTER TABLE {table} DROP COLUMN id;
                    ALTER TABLE {table} RENAME COLUMN uuid_id TO id;
                    ALTER TABLE {table} ALTER COLUMN id SET NOT NULL;
                    ALTER TABLE {table} ADD PRIMARY KEY (id);
                    {rename_table_sql}
                """),
            ],
            state_operations=[
                migrations.RemoveField(model_name=model, name="id"),
                migrations.RenameField(model_name=model, old_name="uuid_id", new_name="id"),
                migrations.AlterField(
                    model_name=model,
                    name="id",
                    field=models.UUIDField(
                        default=uuid.uuid7, editable=False, primary_key=True, serialize=False
                    ),
                ),
                *([migrations.RenameModel(old_name=model, new_name=new_model)] if new_model else []),
            ],
        ),
        migrations.AddField(
            model_name=final_model,
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name=final_model,
            constraint=models.UniqueConstraint(fields=("name",), name=unique_name),
        ),
    ]


class Migration(migrations.Migration):

    dependencies = [
        ("iam", "0006_v2_0_0"),
        ("sta", "0008_remove_observation_result_qualifiers_and_more"),
        ("monitoring", "0001_initial"),
        ("products", "0003_remove_dataproducttransformation_max_gap_interval_and_more"),
    ]

    operations = [
        migrations.RunPython(check_constraints_immediately),

        # --- Thing -> MonitoringSite, merging in Location -----------------------------
        migrations.RenameModel(old_name="Thing", new_name="MonitoringSite"),
        migrations.RenameField(model_name="monitoringsite", old_name="sampling_feature_code", new_name="code"),
        migrations.RenameField(model_name="monitoringsite", old_name="site_type", new_name="type"),
        migrations.RemoveField(model_name="monitoringsite", name="sampling_feature_type"),
        migrations.RenameField(model_name="datastream", old_name="thing", new_name="monitoring_site"),
        migrations.AlterField(
            model_name="monitoringsite",
            name="workspace",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="monitoring_sites",
                to="iam.workspace",
            ),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="latitude",
            field=models.DecimalField(blank=True, decimal_places=16, max_digits=22, null=True),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="longitude",
            field=models.DecimalField(blank=True, decimal_places=16, max_digits=22, null=True),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="elevation_m",
            field=models.DecimalField(blank=True, decimal_places=16, max_digits=22, null=True),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="elevation_datum",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="admin_area_1",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="admin_area_2",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="country",
            field=models.CharField(blank=True, max_length=2, null=True),
        ),
        migrations.RunPython(copy_locations_to_monitoring_sites),
        migrations.AlterField(
            model_name="monitoringsite",
            name="latitude",
            field=models.DecimalField(decimal_places=16, max_digits=22),
        ),
        migrations.AlterField(
            model_name="monitoringsite",
            name="longitude",
            field=models.DecimalField(decimal_places=16, max_digits=22),
        ),
        migrations.DeleteModel(name="Location"),
        migrations.DeleteModel(name="SamplingFeatureType"),

        # --- Sensor -> Method ---------------------------------------------------------
        migrations.RenameModel(old_name="Sensor", new_name="Method"),
        migrations.RenameField(model_name="method", old_name="method_code", new_name="code"),
        migrations.RenameField(model_name="method", old_name="method_type", new_name="type"),
        migrations.RenameField(model_name="method", old_name="method_link", new_name="definition"),
        migrations.RenameField(model_name="method", old_name="manufacturer", new_name="sensor_model_manufacturer"),
        migrations.RenameField(model_name="method", old_name="sensor_model_link", new_name="sensor_model_definition"),
        migrations.RemoveField(model_name="method", name="encoding_type"),
        migrations.RenameField(model_name="datastream", old_name="sensor", new_name="method"),
        migrations.AlterField(
            model_name="method",
            name="code",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="method",
            name="type",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="method",
            name="definition",
            field=models.URLField(blank=True, max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name="method",
            name="sensor_model_definition",
            field=models.URLField(blank=True, max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name="method",
            name="workspace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="methods",
                to="iam.workspace",
            ),
        ),
        migrations.DeleteModel(name="SensorEncodingType"),

        # --- Tags -> JSON -------------------------------------------------------------
        migrations.AddField(
            model_name="monitoringsite",
            name="tags",
            field=models.JSONField(
                blank=True, default=dict, validators=[core.sta.models.validators.validate_tags]
            ),
        ),
        migrations.AddField(
            model_name="datastream",
            name="tags",
            field=models.JSONField(
                blank=True, default=dict, validators=[core.sta.models.validators.validate_tags]
            ),
        ),
        migrations.RunPython(copy_tags_to_json),
        migrations.AddIndex(
            model_name="monitoringsite",
            index=GinIndex(fields=["tags"], name="sta_monitoringsite_tags_gin", opclasses=["jsonb_path_ops"]),
        ),
        migrations.AddIndex(
            model_name="datastream",
            index=GinIndex(fields=["tags"], name="sta_datastream_tags_gin", opclasses=["jsonb_path_ops"]),
        ),
        migrations.DeleteModel(name="ThingTag"),
        migrations.DeleteModel(name="DatastreamTag"),

        # --- File attachments -> linked resources -------------------------------------
        migrations.RenameModel(old_name="ThingFileAttachment", new_name="MonitoringSiteLinkedResource"),
        migrations.RenameModel(old_name="DatastreamFileAttachment", new_name="DatastreamLinkedResource"),
        migrations.RenameField(model_name="monitoringsitelinkedresource", old_name="thing", new_name="monitoring_site"),
        migrations.RenameField(model_name="monitoringsitelinkedresource", old_name="file_attachment", new_name="file"),
        migrations.RenameField(model_name="monitoringsitelinkedresource", old_name="file_attachment_type", new_name="type"),
        migrations.RenameField(model_name="datastreamlinkedresource", old_name="file_attachment", new_name="file"),
        migrations.RenameField(model_name="datastreamlinkedresource", old_name="file_attachment_type", new_name="type"),
        migrations.AlterField(
            model_name="monitoringsitelinkedresource",
            name="monitoring_site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="monitoring_site_linked_resources",
                to="sta.monitoringsite",
            ),
        ),
        migrations.AlterField(
            model_name="datastreamlinkedresource",
            name="datastream",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="datastream_linked_resources",
                to="sta.datastream",
            ),
        ),
        migrations.AlterField(
            model_name="monitoringsitelinkedresource",
            name="file",
            field=models.FileField(
                blank=True,
                default="",
                upload_to=core.sta.models.monitoring_site.monitoring_site_file_attachment_storage_path,
            ),
        ),
        migrations.AlterField(
            model_name="datastreamlinkedresource",
            name="file",
            field=models.FileField(
                blank=True,
                default="",
                upload_to=core.sta.models.datastream.datastream_file_attachment_storage_path,
            ),
        ),
        migrations.AddField(
            model_name="monitoringsitelinkedresource",
            name="url",
            field=models.URLField(blank=True, default="", max_length=2000),
        ),
        migrations.AddField(
            model_name="datastreamlinkedresource",
            name="url",
            field=models.URLField(blank=True, default="", max_length=2000),
        ),
        migrations.AddConstraint(
            model_name="monitoringsitelinkedresource",
            constraint=models.CheckConstraint(
                condition=(
                    (models.Q(file="") & ~models.Q(url=""))
                    | (~models.Q(file="") & models.Q(url=""))
                ),
                name="monitoring_site_linked_resource_file_xor_url",
            ),
        ),
        migrations.AddConstraint(
            model_name="datastreamlinkedresource",
            constraint=models.CheckConstraint(
                condition=(
                    (models.Q(file="") & ~models.Q(url=""))
                    | (~models.Q(file="") & models.Q(url=""))
                ),
                name="datastream_linked_resource_file_xor_url",
            ),
        ),
        # Swap the implicit BigAutoField primary keys for UUIDs. AddField with a callable
        # default evaluates it once for every existing row, so the backfill is row-by-row.
        migrations.AddField(
            model_name="monitoringsitelinkedresource",
            name="uuid_id",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="datastreamlinkedresource",
            name="uuid_id",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(_backfill_uuids("MonitoringSiteLinkedResource")),
        migrations.RunPython(_backfill_uuids("DatastreamLinkedResource")),
        migrations.RemoveField(model_name="monitoringsitelinkedresource", name="id"),
        migrations.RemoveField(model_name="datastreamlinkedresource", name="id"),
        migrations.RenameField(model_name="monitoringsitelinkedresource", old_name="uuid_id", new_name="id"),
        migrations.RenameField(model_name="datastreamlinkedresource", old_name="uuid_id", new_name="id"),
        migrations.AlterField(
            model_name="monitoringsitelinkedresource",
            name="id",
            field=models.UUIDField(default=uuid.uuid7, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="datastreamlinkedresource",
            name="id",
            field=models.UUIDField(default=uuid.uuid7, editable=False, primary_key=True, serialize=False),
        ),

        # --- ProcessingLevel ----------------------------------------------------------
        migrations.RenameField(model_name="processinglevel", old_name="explanation", new_name="description"),
        migrations.AddField(
            model_name="processinglevel",
            name="name",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.RunPython(migrate_processing_levels),
        migrations.AlterField(
            model_name="processinglevel",
            name="name",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="processinglevel",
            name="description",
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name="processinglevel",
            name="code",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="processinglevel",
            name="definition",
            field=models.URLField(blank=True, max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name="processinglevel",
            name="workspace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="processing_levels",
                to="iam.workspace",
            ),
        ),

        # --- ObservedProperty ---------------------------------------------------------
        migrations.RenameField(model_name="observedproperty", old_name="observed_property_type", new_name="type"),
        migrations.AlterField(
            model_name="observedproperty",
            name="type",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="observedproperty",
            name="code",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="observedproperty",
            name="definition",
            field=models.URLField(blank=True, max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name="observedproperty",
            name="workspace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="observed_properties",
                to="iam.workspace",
            ),
        ),

        # --- Unit ---------------------------------------------------------------------
        migrations.RenameField(model_name="unit", old_name="unit_type", new_name="type"),
        migrations.AlterField(
            model_name="unit",
            name="definition",
            field=models.URLField(blank=True, max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name="unit",
            name="workspace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="units",
                to="iam.workspace",
            ),
        ),

        # --- ResultQualifier: code -> name --------------------------------------------
        migrations.RemoveConstraint(model_name="resultqualifier", name="unique_scoped_result_qualifier_code"),
        migrations.RenameField(model_name="resultqualifier", old_name="code", new_name="name"),
        migrations.AlterField(
            model_name="resultqualifier",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="resultqualifier",
            name="workspace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="result_qualifiers",
                to="iam.workspace",
            ),
        ),
        migrations.AddConstraint(
            model_name="resultqualifier",
            constraint=models.UniqueConstraint(
                fields=("name", "workspace_id"),
                name="unique_scoped_result_qualifier_name",
                nulls_distinct=False,
            ),
        ),

        # --- Datastream foreign keys --------------------------------------------------
        migrations.AlterField(
            model_name="datastream",
            name="monitoring_site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="datastreams",
                to="sta.monitoringsite",
            ),
        ),
        migrations.AlterField(
            model_name="datastream",
            name="method",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="datastreams",
                to="sta.method",
            ),
        ),
        migrations.AlterField(
            model_name="datastream",
            name="observed_property",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="datastreams",
                to="sta.observedproperty",
            ),
        ),
        migrations.AlterField(
            model_name="datastream",
            name="processing_level",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="datastreams",
                to="sta.processinglevel",
            ),
        ),
        migrations.AlterField(
            model_name="datastream",
            name="unit",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="datastreams",
                to="sta.unit",
            ),
        ),

        # --- Vocabulary tables --------------------------------------------------------
        migrations.RenameModel(old_name="FileAttachmentType", new_name="LinkedResourceType"),
        migrations.AlterModelManagers(name="sitetype", managers=[]),
        *_vocabulary_operations(
            "sampledmedium", "sta_sampledmedium", "sta_sampledmedium_pkey",
            "unique_sampled_medium_name",
        ),
        *_vocabulary_operations(
            "datastreamaggregation", "sta_datastreamaggregation", "sta_datastreamaggregation_pkey",
            "unique_aggregation_statistic_name",
            new_model="aggregationstatistic", new_table="sta_aggregationstatistic",
        ),
        *_vocabulary_operations(
            "datastreamstatus", "sta_datastreamstatus", "sta_datastreamstatus_pkey",
            "unique_datastream_status_name",
        ),
        *_vocabulary_operations(
            "methodtype", "sta_methodtype", "sta_methodtype_pkey",
            "unique_method_type_name",
        ),
        *_vocabulary_operations(
            "unittype", "sta_unittype", "sta_unittype_pkey",
            "unique_unit_type_name",
        ),
        *_vocabulary_operations(
            "variabletype", "sta_variabletype", "sta_variabletype_pkey",
            "unique_observed_property_type_name",
            new_model="observedpropertytype", new_table="sta_observedpropertytype",
        ),
        *_vocabulary_operations(
            "sitetype", "sta_sitetype", "sta_sitetype_pkey",
            "unique_monitoring_site_type_name",
            new_model="monitoringsitetype", new_table="sta_monitoringsitetype",
        ),
        # The table was renamed from sta_fileattachmenttype above; Postgres keeps the
        # original primary key constraint name.
        *_vocabulary_operations(
            "linkedresourcetype", "sta_linkedresourcetype", "sta_fileattachmenttype_pkey",
            "unique_linked_resource_type_name",
        ),

        # --- Full-text search ---------------------------------------------------------
        *[
            migrations.AddField(
                model_name=model,
                name="search_vector",
                field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
            )
            for _, model, _, _ in SEARCH_VECTORS
        ],
        *[
            operation
            for table, _, _, field_weights in SEARCH_VECTORS
            for operation in _search_vector_trigger_sql(table, field_weights)
        ],
        *[
            migrations.AddIndex(
                model_name=model,
                index=django.contrib.postgres.indexes.GinIndex(fields=["search_vector"], name=index_name),
            )
            for _, model, index_name, _ in SEARCH_VECTORS
        ],
    ]
