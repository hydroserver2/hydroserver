"""
Replace Datastream.is_visible with Datastream.is_restricted.

is_restricted is the inverse of is_visible: a restricted datastream stays publicly
visible, but its observations can only be read by principals with view permission on
Observation in its workspace. Existing values are inverted so behavior is preserved.
"""

from django.db import migrations, models


INVERT_IS_RESTRICTED_SQL = "UPDATE sta_datastream SET is_restricted = NOT is_restricted"


class Migration(migrations.Migration):

    dependencies = [
        ("sta", "0009_v2_0_0"),
    ]

    operations = [
        migrations.RenameField(
            model_name="datastream",
            old_name="is_visible",
            new_name="is_restricted",
        ),
        migrations.RunSQL(
            sql=INVERT_IS_RESTRICTED_SQL,
            reverse_sql=INVERT_IS_RESTRICTED_SQL,
        ),
        migrations.AlterField(
            model_name="datastream",
            name="is_restricted",
            field=models.BooleanField(default=False),
        ),
    ]
