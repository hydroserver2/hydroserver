from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("etl", "0003_remove_datasource_orchestration_system_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="task_type",
            field=models.CharField(default="ETL", max_length=32),
        ),
        migrations.AlterField(
            model_name="task",
            name="data_connection",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tasks",
                to="etl.dataconnection",
            ),
        ),
    ]
