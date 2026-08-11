from django.db import migrations, models


def migrate_processing_level_fields(apps, schema_editor):
    ProcessingLevel = apps.get_model("sta", "ProcessingLevel")

    for processing_level in ProcessingLevel.objects.all().iterator():
        processing_level.name = (
            processing_level.definition or processing_level.code
        )[:255]
        processing_level.definition = None
        processing_level.description = processing_level.description or ""
        processing_level.save(update_fields=["name", "definition", "description"])


def prepare_reverse_migration(apps, schema_editor):
    ObservedProperty = apps.get_model("sta", "ObservedProperty")
    ProcessingLevel = apps.get_model("sta", "ProcessingLevel")
    Unit = apps.get_model("sta", "Unit")

    ObservedProperty.objects.filter(definition__isnull=True).update(definition="")
    Unit.objects.filter(definition__isnull=True).update(definition="")

    for processing_level in ProcessingLevel.objects.all().iterator():
        processing_level.definition = processing_level.name
        processing_level.save(update_fields=["definition"])


class Migration(migrations.Migration):
    dependencies = [
        ("sta", "0013_rename_sensor_method"),
    ]

    operations = [
        migrations.RenameField(
            model_name="processinglevel",
            old_name="explanation",
            new_name="description",
        ),
        migrations.AddField(
            model_name="processinglevel",
            name="name",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.RunPython(
            migrate_processing_level_fields,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="processinglevel",
            name="name",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="processinglevel",
            name="description",
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name="processinglevel",
            name="definition",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RenameField(
            model_name="observedproperty",
            old_name="observed_property_type",
            new_name="type",
        ),
        migrations.AlterField(
            model_name="observedproperty",
            name="definition",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RenameField(
            model_name="unit",
            old_name="unit_type",
            new_name="type",
        ),
        migrations.AlterField(
            model_name="unit",
            name="definition",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunPython(
            migrations.RunPython.noop,
            prepare_reverse_migration,
        ),
    ]
