"""
HydroServer v1.12 -> v2.0.0 schema migration for the quality app.

This migration is forward-only. Back up the database before applying it. See the
"Migrating from HydroServer v1 to v2" deployment guide.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quality", "0002_qcoperation_created_by"),
    ]

    operations = [
        migrations.AlterConstraint(
            model_name="qcsession",
            name="unique_in_progress_session_per_history",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "in_progress")),
                fields=("history",),
                name="unique_in_progress_session_per_history",
                violation_error_code="unique",
            ),
        ),
    ]
