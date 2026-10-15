"""
HydroServer v1.12 -> v2.0.0 schema and data migration for the products app.

This migration is forward-only. Back up the database before applying it. See the
"Migrating from HydroServer v1 to v2" deployment guide for the manual data fixes this
migration requires and the data it drops or transforms.
"""

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

    return [migrations.RunSQL(sql=forward_sql)]


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0003_remove_dataproducttransformation_max_gap_interval_and_more"),
        ("sta", "0009_v2_0_0"),
    ]

    operations = [
        migrations.RenameField(
            model_name="dataproducttask",
            old_name="thing",
            new_name="monitoring_site",
        ),
        migrations.AlterField(
            model_name="dataproducttask",
            name="monitoring_site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="data_product_tasks",
                to="sta.monitoringsite",
            ),
        ),
        migrations.RenameField(
            model_name="ratingcurve",
            old_name="thing",
            new_name="monitoring_site",
        ),
        migrations.AlterField(
            model_name="ratingcurve",
            name="monitoring_site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rating_curves",
                to="sta.monitoringsite",
            ),
        ),
        migrations.AddConstraint(
            model_name="ratingcurvepoint",
            constraint=models.UniqueConstraint(
                fields=("rating_curve", "input_value"),
                name="unique_rating_curve_point_input_value",
                violation_error_message="A point with this input_value already exists on this rating curve.",
            ),
        ),
        migrations.AddField(
            model_name="ratingcurve",
            name="search_vector",
            field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
        ),
        *_search_vector_trigger_sql(
            "products_ratingcurve", {"name": "A", "description": "B", "fitting_method": "C"}
        ),
        migrations.AddIndex(
            model_name="ratingcurve",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["search_vector"], name="products_ratingcurve_search"
            ),
        ),
    ]
