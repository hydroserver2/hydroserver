import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0003_remove_dataproducttransformation_max_gap_interval_and_more"),
        ("sta", "0012_monitoring_site"),
    ]

    operations = [
        migrations.RenameField(
            model_name="dataproducttask",
            old_name="thing",
            new_name="monitoring_site",
        ),
        migrations.AlterField(
            model_name="dataproducttask",
            name="monitoring_site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="data_product_tasks",
                to="sta.monitoringsite",
            ),
        ),
        migrations.RenameField(
            model_name="ratingcurve",
            old_name="thing",
            new_name="monitoring_site",
        ),
        migrations.AlterField(
            model_name="ratingcurve",
            name="monitoring_site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rating_curves",
                to="sta.monitoringsite",
            ),
        ),
    ]
