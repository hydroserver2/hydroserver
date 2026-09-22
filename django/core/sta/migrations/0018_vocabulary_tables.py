import uuid

import django.contrib.postgres.indexes
import django.contrib.postgres.search
import django.db.models.deletion
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
    touches unrelated columns. INSERT has no OLD row to compare against, so it always
    runs unconditionally.
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

    reverse_sql = f"""
        DROP TRIGGER IF EXISTS {insert_trigger_name} ON {table};
        DROP TRIGGER IF EXISTS {update_trigger_name} ON {table};
        DROP FUNCTION IF EXISTS {function_name}();
    """

    return [migrations.RunSQL(sql=forward_sql, reverse_sql=reverse_sql)]


def _backfill_sampled_medium_uuids(apps, schema_editor):
    SampledMedium = apps.get_model("sta", "SampledMedium")
    for row in SampledMedium.objects.all():
        row.uuid_id = uuid.uuid7()
        row.save(update_fields=["uuid_id"])


def _backfill_aggregation_statistic_uuids(apps, schema_editor):
    # Still the pre-rename historical model at this point in the migration.
    DatastreamAggregation = apps.get_model("sta", "DatastreamAggregation")
    for row in DatastreamAggregation.objects.all():
        row.uuid_id = uuid.uuid7()
        row.save(update_fields=["uuid_id"])


def _backfill_datastream_status_uuids(apps, schema_editor):
    DatastreamStatus = apps.get_model("sta", "DatastreamStatus")
    for row in DatastreamStatus.objects.all():
        row.uuid_id = uuid.uuid7()
        row.save(update_fields=["uuid_id"])


def _backfill_method_type_uuids(apps, schema_editor):
    MethodType = apps.get_model("sta", "MethodType")
    for row in MethodType.objects.all():
        row.uuid_id = uuid.uuid7()
        row.save(update_fields=["uuid_id"])


def _backfill_unit_type_uuids(apps, schema_editor):
    UnitType = apps.get_model("sta", "UnitType")
    for row in UnitType.objects.all():
        row.uuid_id = uuid.uuid7()
        row.save(update_fields=["uuid_id"])


def _backfill_observed_property_type_uuids(apps, schema_editor):
    # Still the pre-rename historical model at this point in the migration.
    VariableType = apps.get_model("sta", "VariableType")
    for row in VariableType.objects.all():
        row.uuid_id = uuid.uuid7()
        row.save(update_fields=["uuid_id"])


def _backfill_monitoring_site_type_uuids(apps, schema_editor):
    # Still the pre-rename historical model at this point in the migration.
    SiteType = apps.get_model("sta", "SiteType")
    for row in SiteType.objects.all():
        row.uuid_id = uuid.uuid7()
        row.save(update_fields=["uuid_id"])


def _backfill_linked_resource_type_uuids(apps, schema_editor):
    LinkedResourceType = apps.get_model("sta", "LinkedResourceType")
    for row in LinkedResourceType.objects.all():
        row.uuid_id = uuid.uuid7()
        row.save(update_fields=["uuid_id"])


class Migration(migrations.Migration):
    """
    Promotes every bare `name`-only vocabulary lookup table in the sta app to a shared
    shape: UUID id, `name`/`description`, `search_vector`, and a
    `UniqueConstraint(fields=["name"])`. These 8 tables have no workspace concept at all
    (registered with `workspace_field=None` — see core/iam/permissions/registry.py) and
    are publicly viewable, superuser-only to create/edit/delete. `ResultQualifier` is
    folded into this same migration (it's already on this shape, minus the `name` field
    being called `code`) since neither it nor these 8 tables ever shipped with
    `is_active` — that field was added and removed again within this same undeployed
    branch, so it never appears in migration history at all. Unlike the 8, it keeps its
    existing nullable `workspace` FK and a scoped `UniqueConstraint(fields=["name",
    "workspace_id"])` — it's the only one of these tables that's ever user/workspace
    managed, so create/edit/delete for it goes through normal workspace-permission checks
    rather than being superuser-only.

    Three tables are renamed as part of this pass: `DatastreamAggregation` ->
    `AggregationStatistic`, `VariableType` -> `ObservedPropertyType`, `SiteType` ->
    `MonitoringSiteType`. `DatastreamStatus`, `MethodType`, `UnitType`, and
    `LinkedResourceType` keep their names. `ResultQualifier`'s `code` field is renamed to
    `name` to match every other table here.

    Each of the 8 non-`ResultQualifier` tables' block follows the same order: add a
    nullable UUID column, backfill a distinct uuid7 per existing row, enforce
    non-null/unique on it, drop the old bare `unique=True` on `name`, swap the primary key
    from the old BigAutoField `id` to the UUID column (renaming the table/model here too,
    for the three renamed tables) via raw SQL (not expressible as ordinary field
    operations), *then* add `description`, the bare `UniqueConstraint`, and the
    `search_vector` field/trigger/index.

    `LinkedResourceType`'s actual PK constraint is named `sta_fileattachmenttype_pkey`,
    not `sta_linkedresourcetype_pkey`: this table was itself renamed from
    `FileAttachmentType` in migration 0015, and Postgres doesn't rename
    constraints/indexes when a table is renamed, so the old name stuck.
    """

    dependencies = [
        ('iam', '0012_workspace_search_vector_and_more'),
        ('sta', '0017_datastream_search_vector_method_search_vector_and_more'),
    ]

    operations = [
        # --- SampledMedium ------------------------------------------------------------
        migrations.AddField(
            model_name='sampledmedium',
            name='uuid_id',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(_backfill_sampled_medium_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='sampledmedium',
            name='uuid_id',
            field=models.UUIDField(editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='sampledmedium',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE sta_sampledmedium DROP CONSTRAINT sta_sampledmedium_pkey;
                        ALTER TABLE sta_sampledmedium DROP COLUMN id;
                        ALTER TABLE sta_sampledmedium RENAME COLUMN uuid_id TO id;
                        ALTER TABLE sta_sampledmedium ADD PRIMARY KEY (id);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(model_name='sampledmedium', name='id'),
                migrations.RenameField(model_name='sampledmedium', old_name='uuid_id', new_name='id'),
                migrations.AlterField(
                    model_name='sampledmedium',
                    name='id',
                    field=models.UUIDField(default=uuid.uuid7, editable=False, primary_key=True, serialize=False),
                ),
            ],
        ),
        migrations.AddField(
            model_name='sampledmedium',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddConstraint(
            model_name='sampledmedium',
            constraint=models.UniqueConstraint(
                fields=('name',),
                name='unique_sampled_medium_name',
            ),
        ),
        migrations.AddField(
            model_name='sampledmedium',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
        ),
        *_search_vector_trigger_sql(
            "sta_sampledmedium", {"description": "A", "name": "C"}
        ),
        migrations.AddIndex(
            model_name='sampledmedium',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='sta_sampledmed_search_gin'),
        ),

        # --- AggregationStatistic (renamed from DatastreamAggregation) ----------------
        migrations.AddField(
            model_name='datastreamaggregation',
            name='uuid_id',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(_backfill_aggregation_statistic_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='datastreamaggregation',
            name='uuid_id',
            field=models.UUIDField(editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='datastreamaggregation',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE sta_datastreamaggregation DROP CONSTRAINT sta_datastreamaggregation_pkey;
                        ALTER TABLE sta_datastreamaggregation DROP COLUMN id;
                        ALTER TABLE sta_datastreamaggregation RENAME COLUMN uuid_id TO id;
                        ALTER TABLE sta_datastreamaggregation ADD PRIMARY KEY (id);
                        ALTER TABLE sta_datastreamaggregation RENAME TO sta_aggregationstatistic;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(model_name='datastreamaggregation', name='id'),
                migrations.RenameField(model_name='datastreamaggregation', old_name='uuid_id', new_name='id'),
                migrations.AlterField(
                    model_name='datastreamaggregation',
                    name='id',
                    field=models.UUIDField(default=uuid.uuid7, editable=False, primary_key=True, serialize=False),
                ),
                migrations.RenameModel(old_name='datastreamaggregation', new_name='aggregationstatistic'),
            ],
        ),
        migrations.AddField(
            model_name='aggregationstatistic',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddConstraint(
            model_name='aggregationstatistic',
            constraint=models.UniqueConstraint(
                fields=('name',),
                name='unique_aggregation_statistic_name',
            ),
        ),
        migrations.AddField(
            model_name='aggregationstatistic',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
        ),
        *_search_vector_trigger_sql(
            "sta_aggregationstatistic", {"description": "A", "name": "C"}
        ),
        migrations.AddIndex(
            model_name='aggregationstatistic',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='sta_aggstat_search_gin'),
        ),

        # --- DatastreamStatus -----------------------------------------------------------
        migrations.AddField(
            model_name='datastreamstatus',
            name='uuid_id',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(_backfill_datastream_status_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='datastreamstatus',
            name='uuid_id',
            field=models.UUIDField(editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='datastreamstatus',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE sta_datastreamstatus DROP CONSTRAINT sta_datastreamstatus_pkey;
                        ALTER TABLE sta_datastreamstatus DROP COLUMN id;
                        ALTER TABLE sta_datastreamstatus RENAME COLUMN uuid_id TO id;
                        ALTER TABLE sta_datastreamstatus ADD PRIMARY KEY (id);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(model_name='datastreamstatus', name='id'),
                migrations.RenameField(model_name='datastreamstatus', old_name='uuid_id', new_name='id'),
                migrations.AlterField(
                    model_name='datastreamstatus',
                    name='id',
                    field=models.UUIDField(default=uuid.uuid7, editable=False, primary_key=True, serialize=False),
                ),
            ],
        ),
        migrations.AddField(
            model_name='datastreamstatus',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddConstraint(
            model_name='datastreamstatus',
            constraint=models.UniqueConstraint(
                fields=('name',),
                name='unique_datastream_status_name',
            ),
        ),
        migrations.AddField(
            model_name='datastreamstatus',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
        ),
        *_search_vector_trigger_sql(
            "sta_datastreamstatus", {"description": "A", "name": "C"}
        ),
        migrations.AddIndex(
            model_name='datastreamstatus',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='sta_dsstatus_search_gin'),
        ),

        # --- MethodType -------------------------------------------------------------
        migrations.AddField(
            model_name='methodtype',
            name='uuid_id',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(_backfill_method_type_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='methodtype',
            name='uuid_id',
            field=models.UUIDField(editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='methodtype',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE sta_methodtype DROP CONSTRAINT sta_methodtype_pkey;
                        ALTER TABLE sta_methodtype DROP COLUMN id;
                        ALTER TABLE sta_methodtype RENAME COLUMN uuid_id TO id;
                        ALTER TABLE sta_methodtype ADD PRIMARY KEY (id);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(model_name='methodtype', name='id'),
                migrations.RenameField(model_name='methodtype', old_name='uuid_id', new_name='id'),
                migrations.AlterField(
                    model_name='methodtype',
                    name='id',
                    field=models.UUIDField(default=uuid.uuid7, editable=False, primary_key=True, serialize=False),
                ),
            ],
        ),
        migrations.AddField(
            model_name='methodtype',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddConstraint(
            model_name='methodtype',
            constraint=models.UniqueConstraint(
                fields=('name',),
                name='unique_method_type_name',
            ),
        ),
        migrations.AddField(
            model_name='methodtype',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
        ),
        *_search_vector_trigger_sql(
            "sta_methodtype", {"description": "A", "name": "C"}
        ),
        migrations.AddIndex(
            model_name='methodtype',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='sta_methodtype_search_gin'),
        ),

        # --- UnitType -----------------------------------------------------------------
        migrations.AddField(
            model_name='unittype',
            name='uuid_id',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(_backfill_unit_type_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='unittype',
            name='uuid_id',
            field=models.UUIDField(editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='unittype',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE sta_unittype DROP CONSTRAINT sta_unittype_pkey;
                        ALTER TABLE sta_unittype DROP COLUMN id;
                        ALTER TABLE sta_unittype RENAME COLUMN uuid_id TO id;
                        ALTER TABLE sta_unittype ADD PRIMARY KEY (id);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(model_name='unittype', name='id'),
                migrations.RenameField(model_name='unittype', old_name='uuid_id', new_name='id'),
                migrations.AlterField(
                    model_name='unittype',
                    name='id',
                    field=models.UUIDField(default=uuid.uuid7, editable=False, primary_key=True, serialize=False),
                ),
            ],
        ),
        migrations.AddField(
            model_name='unittype',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddConstraint(
            model_name='unittype',
            constraint=models.UniqueConstraint(
                fields=('name',),
                name='unique_unit_type_name',
            ),
        ),
        migrations.AddField(
            model_name='unittype',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
        ),
        *_search_vector_trigger_sql(
            "sta_unittype", {"description": "A", "name": "C"}
        ),
        migrations.AddIndex(
            model_name='unittype',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='sta_unittype_search_gin'),
        ),

        # --- ObservedPropertyType (renamed from VariableType) --------------------------
        migrations.AddField(
            model_name='variabletype',
            name='uuid_id',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(_backfill_observed_property_type_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='variabletype',
            name='uuid_id',
            field=models.UUIDField(editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='variabletype',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE sta_variabletype DROP CONSTRAINT sta_variabletype_pkey;
                        ALTER TABLE sta_variabletype DROP COLUMN id;
                        ALTER TABLE sta_variabletype RENAME COLUMN uuid_id TO id;
                        ALTER TABLE sta_variabletype ADD PRIMARY KEY (id);
                        ALTER TABLE sta_variabletype RENAME TO sta_observedpropertytype;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(model_name='variabletype', name='id'),
                migrations.RenameField(model_name='variabletype', old_name='uuid_id', new_name='id'),
                migrations.AlterField(
                    model_name='variabletype',
                    name='id',
                    field=models.UUIDField(default=uuid.uuid7, editable=False, primary_key=True, serialize=False),
                ),
                migrations.RenameModel(old_name='variabletype', new_name='observedpropertytype'),
            ],
        ),
        migrations.AddField(
            model_name='observedpropertytype',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddConstraint(
            model_name='observedpropertytype',
            constraint=models.UniqueConstraint(
                fields=('name',),
                name='unique_observed_property_type_name',
            ),
        ),
        migrations.AddField(
            model_name='observedpropertytype',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
        ),
        *_search_vector_trigger_sql(
            "sta_observedpropertytype", {"description": "A", "name": "C"}
        ),
        migrations.AddIndex(
            model_name='observedpropertytype',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='sta_optype_search_gin'),
        ),

        # --- MonitoringSiteType (renamed from SiteType) ---------------------------------
        migrations.AlterModelManagers(
            name='sitetype',
            managers=[],
        ),
        migrations.AddField(
            model_name='sitetype',
            name='uuid_id',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(_backfill_monitoring_site_type_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='sitetype',
            name='uuid_id',
            field=models.UUIDField(editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='sitetype',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE sta_sitetype DROP CONSTRAINT sta_sitetype_pkey;
                        ALTER TABLE sta_sitetype DROP COLUMN id;
                        ALTER TABLE sta_sitetype RENAME COLUMN uuid_id TO id;
                        ALTER TABLE sta_sitetype ADD PRIMARY KEY (id);
                        ALTER TABLE sta_sitetype RENAME TO sta_monitoringsitetype;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(model_name='sitetype', name='id'),
                migrations.RenameField(model_name='sitetype', old_name='uuid_id', new_name='id'),
                migrations.AlterField(
                    model_name='sitetype',
                    name='id',
                    field=models.UUIDField(default=uuid.uuid7, editable=False, primary_key=True, serialize=False),
                ),
                migrations.RenameModel(old_name='sitetype', new_name='monitoringsitetype'),
            ],
        ),
        migrations.AddField(
            model_name='monitoringsitetype',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddConstraint(
            model_name='monitoringsitetype',
            constraint=models.UniqueConstraint(
                fields=('name',),
                name='unique_monitoring_site_type_name',
            ),
        ),
        migrations.AddField(
            model_name='monitoringsitetype',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
        ),
        *_search_vector_trigger_sql(
            "sta_monitoringsitetype", {"description": "A", "name": "C"}
        ),
        migrations.AddIndex(
            model_name='monitoringsitetype',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='sta_sitetype_search_gin'),
        ),

        # --- LinkedResourceType ---------------------------------------------------------
        migrations.AddField(
            model_name='linkedresourcetype',
            name='uuid_id',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(_backfill_linked_resource_type_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='linkedresourcetype',
            name='uuid_id',
            field=models.UUIDField(editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='linkedresourcetype',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE sta_linkedresourcetype DROP CONSTRAINT sta_fileattachmenttype_pkey;
                        ALTER TABLE sta_linkedresourcetype DROP COLUMN id;
                        ALTER TABLE sta_linkedresourcetype RENAME COLUMN uuid_id TO id;
                        ALTER TABLE sta_linkedresourcetype ADD PRIMARY KEY (id);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(model_name='linkedresourcetype', name='id'),
                migrations.RenameField(model_name='linkedresourcetype', old_name='uuid_id', new_name='id'),
                migrations.AlterField(
                    model_name='linkedresourcetype',
                    name='id',
                    field=models.UUIDField(default=uuid.uuid7, editable=False, primary_key=True, serialize=False),
                ),
            ],
        ),
        migrations.AddField(
            model_name='linkedresourcetype',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddConstraint(
            model_name='linkedresourcetype',
            constraint=models.UniqueConstraint(
                fields=('name',),
                name='unique_linked_resource_type_name',
            ),
        ),
        migrations.AddField(
            model_name='linkedresourcetype',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
        ),
        *_search_vector_trigger_sql(
            "sta_linkedresourcetype", {"description": "A", "name": "C"}
        ),
        migrations.AddIndex(
            model_name='linkedresourcetype',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='sta_linkedrestype_search_gin'),
        ),
    
        # --- ResultQualifier (code -> name; keeps its existing workspace FK) -----------
        migrations.RemoveConstraint(
            model_name='resultqualifier',
            name='unique_scoped_result_qualifier_code',
        ),
        migrations.RenameField(
            model_name='resultqualifier',
            old_name='code',
            new_name='name',
        ),
        migrations.AlterField(
            model_name='resultqualifier',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddConstraint(
            model_name='resultqualifier',
            constraint=models.UniqueConstraint(
                fields=('name', 'workspace_id'),
                name='unique_scoped_result_qualifier_name',
                nulls_distinct=False,
            ),
        ),
        *_search_vector_trigger_sql(
            "sta_resultqualifier", {"description": "A", "name": "C"}
        ),
    ]
