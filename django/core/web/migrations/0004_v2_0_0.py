"""
HydroServer v1.12 -> v2.0.0 schema and data migration for the web app.

This migration is forward-only. Back up the database before applying it. See the
"Migrating from HydroServer v1 to v2" deployment guide for the manual data fixes this
migration requires and the data it drops or transforms.
"""

from django.core.management import call_command
from django.db import migrations


CACHE_TABLE_NAME = "web_cache"


def create_cache_table(apps, schema_editor):
    call_command("createcachetable", CACHE_TABLE_NAME)


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0003_google_analytics"),
    ]

    operations = [
        migrations.RunPython(create_cache_table),
    ]
