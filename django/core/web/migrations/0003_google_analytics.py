from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0002_sitetypeicon"),
    ]

    operations = [
        migrations.AddField(
            model_name="analyticsconfiguration",
            name="enable_google_analytics",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="analyticsconfiguration",
            name="google_analytics_measurement_id",
            field=models.CharField(
                blank=True,
                help_text="Google Analytics 4 measurement ID (for example, G-XXXXXXXXXX).",
                max_length=255,
                null=True,
            ),
        ),
    ]
