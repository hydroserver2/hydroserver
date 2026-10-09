"""
HydroServer v1.12 -> v2.0.0 schema and data migration for the monitoring app.

This migration is forward-only. Back up the database before applying it. See the
"Migrating from HydroServer v1 to v2" deployment guide for the manual data fixes this
migration requires and the data it drops or transforms.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitoring", "0001_initial"),
        ("sta", "0009_v2_0_0"),
    ]

    operations = [
        migrations.RenameField(
            model_name="monitoringtask",
            old_name="thing",
            new_name="monitoring_site",
        ),
        migrations.AlterField(
            model_name="monitoringtask",
            name="monitoring_site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="monitoring_tasks",
                to="sta.monitoringsite",
            ),
        ),
    ]
