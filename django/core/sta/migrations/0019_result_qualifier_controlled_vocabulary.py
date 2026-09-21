from django.db import migrations, models


def _search_vector_trigger_sql(
    table: str,
    field_weights: dict[str, str],
    vector_column: str = "search_vector",
) -> list[migrations.RunSQL]:
    """
    Builds the migration operations needed to keep a `SearchVectorField` current via a
    Postgres trigger, plus a one-time backfill for existing rows.

    Re-issuing this against `sta_resultqualifier` (its trigger was originally created in
    migration 0017, referencing `code`) is required, not optional: `CREATE OR REPLACE
    FUNCTION` replaces the old function body so it stops referencing the now-renamed
    `code` column, which would otherwise throw on the very next INSERT/UPDATE.
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


class Migration(migrations.Migration):
    """
    Conforms ResultQualifier to the shared controlled-vocabulary shape: renames `code` to
    `name` and adds `is_active`. Unlike the tables in the previous migration, no PK swap
    is needed here (id is already a UUID) and no table/model rename happens, so this is
    just a column rename plus two field changes.
    """

    dependencies = [
        ('sta', '0018_controlled_vocabulary_tables'),
    ]

    operations = [
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
        migrations.AddField(
            model_name='resultqualifier',
            name='is_active',
            field=models.BooleanField(default=True),
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
