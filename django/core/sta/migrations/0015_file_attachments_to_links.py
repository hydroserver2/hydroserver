import uuid

import core.sta.models.datastream
import core.sta.models.monitoring_site
import django.db.models.deletion
from django.db import migrations, models


def populate_link_uuids(apps, schema_editor):
    for model_name in ("MonitoringSiteLinkedResource", "DatastreamLinkedResource"):
        model = apps.get_model("sta", model_name)
        for obj in model.objects.all():
            obj.uuid_id = uuid.uuid7()
            obj.save(update_fields=["uuid_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("sta", "0014_monitoringsite_tags_datastream_tags"),
    ]

    operations = [
        # --- Renames: file attachments -> linked resources ---
        migrations.RenameModel(old_name="MonitoringSiteFileAttachment", new_name="MonitoringSiteLinkedResource"),
        migrations.RenameModel(old_name="DatastreamFileAttachment", new_name="DatastreamLinkedResource"),
        migrations.RenameModel(old_name="FileAttachmentType", new_name="LinkedResourceType"),

        migrations.RenameField(model_name="monitoringsitelinkedresource", old_name="file_attachment", new_name="file"),
        migrations.RenameField(model_name="monitoringsitelinkedresource", old_name="file_attachment_type", new_name="type"),
        migrations.RenameField(model_name="datastreamlinkedresource", old_name="file_attachment", new_name="file"),
        migrations.RenameField(model_name="datastreamlinkedresource", old_name="file_attachment_type", new_name="type"),

        migrations.AlterField(
            model_name="monitoringsitelinkedresource",
            name="file",
            field=models.FileField(
                upload_to=core.sta.models.monitoring_site.monitoring_site_file_attachment_storage_path,
                blank=True,
                default="",
            ),
        ),
        migrations.AlterField(
            model_name="datastreamlinkedresource",
            name="file",
            field=models.FileField(
                upload_to=core.sta.models.datastream.datastream_file_attachment_storage_path,
                blank=True,
                default="",
            ),
        ),

        # --- Add external url field ---
        migrations.AddField(
            model_name="monitoringsitelinkedresource",
            name="url",
            field=models.URLField(blank=True, default="", max_length=2000),
        ),
        migrations.AddField(
            model_name="datastreamlinkedresource",
            name="url",
            field=models.URLField(blank=True, default="", max_length=2000),
        ),

        migrations.AddConstraint(
            model_name="monitoringsitelinkedresource",
            constraint=models.CheckConstraint(
                condition=(
                    (models.Q(file="") & ~models.Q(url="")) |
                    (~models.Q(file="") & models.Q(url=""))
                ),
                name="monitoring_site_linked_resource_file_xor_url",
            ),
        ),
        migrations.AddConstraint(
            model_name="datastreamlinkedresource",
            constraint=models.CheckConstraint(
                condition=(
                    (models.Q(file="") & ~models.Q(url="")) |
                    (~models.Q(file="") & models.Q(url=""))
                ),
                name="datastream_linked_resource_file_xor_url",
            ),
        ),

        # --- Swap PK from implicit BigAutoField to UUIDField ---
        # AddField with a callable default only evaluates the callable once and
        # applies that single value to every existing row, so the UUID backfill
        # is done row-by-row via RunPython instead of a field-level default.
        migrations.AddField(
            model_name="monitoringsitelinkedresource",
            name="uuid_id",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name="datastreamlinkedresource",
            name="uuid_id",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(populate_link_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="monitoringsitelinkedresource",
            name="uuid_id",
            field=models.UUIDField(null=False, editable=False),
        ),
        migrations.AlterField(
            model_name="datastreamlinkedresource",
            name="uuid_id",
            field=models.UUIDField(null=False, editable=False),
        ),
        migrations.RemoveField(model_name="monitoringsitelinkedresource", name="id"),
        migrations.RemoveField(model_name="datastreamlinkedresource", name="id"),
        migrations.RenameField(model_name="monitoringsitelinkedresource", old_name="uuid_id", new_name="id"),
        migrations.RenameField(model_name="datastreamlinkedresource", old_name="uuid_id", new_name="id"),
        migrations.AlterField(
            model_name="monitoringsitelinkedresource",
            name="id",
            field=models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False, serialize=False),
        ),
        migrations.AlterField(
            model_name="datastreamlinkedresource",
            name="id",
            field=models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False, serialize=False),
        ),

        # --- Normalize FK state after RenameModel (no functional change) ---
        migrations.AlterField(
            model_name="monitoringsitelinkedresource",
            name="monitoring_site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="monitoring_site_linked_resources",
                to="sta.monitoringsite",
            ),
        ),
        migrations.AlterField(
            model_name="datastreamlinkedresource",
            name="datastream",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="datastream_linked_resources",
                to="sta.datastream",
            ),
        ),
    ]
