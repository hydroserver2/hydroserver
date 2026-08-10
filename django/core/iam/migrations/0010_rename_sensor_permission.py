from django.db import migrations


def rename_sensor_permissions(apps, schema_editor):
    Permission = apps.get_model("iam", "Permission")
    Permission.objects.filter(resource_type="Sensor").update(resource_type="Method")


def restore_sensor_permissions(apps, schema_editor):
    Permission = apps.get_model("iam", "Permission")
    Permission.objects.filter(resource_type="Method").update(resource_type="Sensor")


class Migration(migrations.Migration):
    dependencies = [
        ("iam", "0009_rename_thing_permission"),
        ("sta", "0013_rename_sensor_method"),
    ]

    operations = [
        migrations.RunPython(rename_sensor_permissions, restore_sensor_permissions),
    ]
