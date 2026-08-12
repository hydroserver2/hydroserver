import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sta", "0012_monitoring_site"),
    ]

    operations = [
        migrations.RenameModel(old_name="Sensor", new_name="Method"),
        migrations.RenameField(
            model_name="method", old_name="method_code", new_name="code"
        ),
        migrations.RenameField(
            model_name="method", old_name="method_type", new_name="type"
        ),
        migrations.RenameField(
            model_name="method", old_name="method_link", new_name="definition"
        ),
        migrations.RenameField(
            model_name="method",
            old_name="manufacturer",
            new_name="sensor_model_manufacturer",
        ),
        migrations.RenameField(
            model_name="method",
            old_name="sensor_model_link",
            new_name="sensor_model_definition",
        ),
        migrations.AlterField(
            model_name="method",
            name="encoding_type",
            field=models.CharField(max_length=255, default="<value>"),
        ),
        migrations.RemoveField(model_name="method", name="encoding_type"),
        migrations.RenameField(
            model_name="datastream", old_name="sensor", new_name="method"
        ),
        migrations.AlterField(
            model_name="method",
            name="workspace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="methods",
                to="iam.workspace",
            ),
        ),
        migrations.DeleteModel(name="SensorEncodingType"),
    ]
