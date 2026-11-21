"""
Add z to the observation unique constraint.

The new constraint treats NULLs as equal (NULLS NOT DISTINCT), so time series observations, whose z is always NULL,
stay unique per phenomenon time, while profile coverage observations are unique per (phenomenon time, z).

The index is built CONCURRENTLY so writes to the observation table aren't blocked while it builds, then attached as
the constraint Django's state expects. The old constraint is dropped last, so uniqueness is enforced throughout.
CONCURRENTLY can't run inside a transaction, so this migration is non-atomic. If the index build fails partway,
drop the invalid index named below before re-running.
"""

from django.db import migrations, models


NEW_CONSTRAINT = "unique_datastream_id_phenomenon_time_z"
OLD_CONSTRAINT = "unique_datastream_id_phenomenon_time"


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("sta", "0011_profile_coverage"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        f"CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {NEW_CONSTRAINT} "
                        f"ON sta_observation (datastream_id, phenomenon_time, z) NULLS NOT DISTINCT"
                    ),
                    reverse_sql=f"DROP INDEX CONCURRENTLY IF EXISTS {NEW_CONSTRAINT}",
                ),
                migrations.RunSQL(
                    sql=f"ALTER TABLE sta_observation ADD CONSTRAINT {NEW_CONSTRAINT} UNIQUE USING INDEX {NEW_CONSTRAINT}",
                    # Dropping the constraint also drops its index, so the reverse of the index step is a no-op.
                    reverse_sql=f"ALTER TABLE sta_observation DROP CONSTRAINT IF EXISTS {NEW_CONSTRAINT}",
                ),
                migrations.RunSQL(
                    sql=f"ALTER TABLE sta_observation DROP CONSTRAINT {OLD_CONSTRAINT}",
                    reverse_sql=(
                        f"ALTER TABLE sta_observation ADD CONSTRAINT {OLD_CONSTRAINT} "
                        f"UNIQUE (datastream_id, phenomenon_time)"
                    ),
                ),
            ],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="observation",
                    name=OLD_CONSTRAINT,
                ),
                migrations.AddConstraint(
                    model_name="observation",
                    constraint=models.UniqueConstraint(
                        fields=("datastream_id", "phenomenon_time", "z"),
                        name=NEW_CONSTRAINT,
                        nulls_distinct=False,
                    ),
                ),
            ],
        ),
    ]
