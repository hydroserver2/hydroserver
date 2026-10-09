"""
HydroServer v1.12 -> v2.0.0 schema and data migration for the etl app.

This migration is forward-only. Back up the database before applying it. See the
"Migrating from HydroServer v1 to v2" deployment guide for the manual data fixes this
migration requires and the data it drops or transforms.
"""

import django.contrib.postgres.indexes
import django.contrib.postgres.search
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

    return [migrations.RunSQL(sql=forward_sql)]


class Migration(migrations.Migration):

    dependencies = [
        ("etl", "0009_payload_data_ingestion_window_end_anchor_and_more"),
        ("iam", "0006_v2_0_0"),
        ("sta", "0009_v2_0_0"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="etlmapping",
            constraint=models.UniqueConstraint(
                fields=("target_datastream",),
                name="unique_etl_mapping_target_datastream",
                violation_error_message="This datastream is already mapped to by another task.",
            ),
        ),
        migrations.AddConstraint(
            model_name="placeholdervariable",
            constraint=models.UniqueConstraint(
                fields=("data_connection", "name", "variable_type"),
                name="unique_placeholder_variable_name_and_type_per_data_connection",
                violation_error_message="A placeholder variable with this name and type already exists on this data connection.",
            ),
        ),
        migrations.AddField(
            model_name="dataconnection",
            name="search_vector",
            field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
        ),
        *_search_vector_trigger_sql(
            "etl_dataconnection", {"name": "A", "description": "B", "timezone_type": "C"}
        ),
        migrations.AddIndex(
            model_name="dataconnection",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["search_vector"], name="etl_dataconn_search_gin"
            ),
        ),
    ]
