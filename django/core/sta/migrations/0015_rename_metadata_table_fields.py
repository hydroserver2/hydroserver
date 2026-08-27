from urllib.parse import urlparse

from django.db import migrations, models


LEGACY_DEFINITION_PREFIX = "[Migrated legacy definition]\n"
LEGACY_DEFINITION_SUFFIX = "\n[/Migrated legacy definition]\n\n"


def is_absolute_uri(value):
    parsed = urlparse(value)
    return bool(parsed.scheme and (parsed.netloc or parsed.path))


def migrate_processing_level_fields(apps, schema_editor):
    ProcessingLevel = apps.get_model("sta", "ProcessingLevel")

    for processing_level in ProcessingLevel.objects.all().iterator():
        legacy_definition = processing_level.definition or ""
        definition_candidate = legacy_definition.strip()
        fallback_name = (processing_level.code or "").strip() or str(
            processing_level.pk
        )
        legacy_description = processing_level.description or ""

        if is_absolute_uri(definition_candidate):
            processing_level.name = fallback_name
            processing_level.definition = definition_candidate
            processing_level.description = legacy_description
        elif len(definition_candidate) <= 255:
            processing_level.name = definition_candidate or fallback_name
            processing_level.definition = None
            processing_level.description = legacy_description
        else:
            processing_level.name = fallback_name
            processing_level.definition = None
            processing_level.description = (
                f"{LEGACY_DEFINITION_PREFIX}{legacy_definition}"
                f"{LEGACY_DEFINITION_SUFFIX}{legacy_description}"
            )

        processing_level.save(update_fields=["name", "definition", "description"])


def prepare_reverse_migration(apps, schema_editor):
    ObservedProperty = apps.get_model("sta", "ObservedProperty")
    ProcessingLevel = apps.get_model("sta", "ProcessingLevel")
    Unit = apps.get_model("sta", "Unit")

    ObservedProperty.objects.filter(definition__isnull=True).update(definition="")
    Unit.objects.filter(definition__isnull=True).update(definition="")

    for processing_level in ProcessingLevel.objects.all().iterator():
        update_fields = ["definition"]
        description = processing_level.description or ""

        if processing_level.definition:
            continue
        if description.startswith(LEGACY_DEFINITION_PREFIX):
            marked_definition = description[len(LEGACY_DEFINITION_PREFIX) :]
            if LEGACY_DEFINITION_SUFFIX in marked_definition:
                legacy_definition, legacy_description = marked_definition.split(
                    LEGACY_DEFINITION_SUFFIX, 1
                )
                processing_level.definition = legacy_definition
                processing_level.description = legacy_description
                update_fields.append("description")
            else:
                processing_level.definition = processing_level.name
        else:
            processing_level.definition = processing_level.name

        processing_level.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("sta", "0014_monitoringsite_tags_datastream_tags"),
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
