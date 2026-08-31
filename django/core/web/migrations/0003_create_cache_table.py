from django.core.management import call_command
from django.db import migrations


CACHE_TABLE_NAME = "web_cache"


def create_cache_table(apps, schema_editor):
    call_command("createcachetable", CACHE_TABLE_NAME)


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0002_sitetypeicon"),
    ]

    operations = [
        migrations.RunPython(create_cache_table, migrations.RunPython.noop),
    ]
