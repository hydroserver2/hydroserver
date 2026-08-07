from django.db import migrations


def rename_thing_permissions(apps, schema_editor):
    Permission = apps.get_model("iam", "Permission")
    Permission.objects.filter(resource_type="Thing").update(
        resource_type="MonitoringSite"
    )


def restore_thing_permissions(apps, schema_editor):
    Permission = apps.get_model("iam", "Permission")
    Permission.objects.filter(resource_type="MonitoringSite").update(
        resource_type="Thing"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("iam", "0008_alter_workspace_owner"),
        ("sta", "0012_monitoring_site"),
    ]

    operations = [
        migrations.RunPython(rename_thing_permissions, restore_thing_permissions),
    ]
