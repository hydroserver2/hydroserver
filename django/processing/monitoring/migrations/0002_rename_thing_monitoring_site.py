import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("monitoring", "0001_initial"),
        ("sta", "0012_monitoring_site"),
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
