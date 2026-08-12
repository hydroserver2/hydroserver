import core.sta.models.monitoring_site
import django.db.models.deletion
from django.db import migrations, models


def copy_locations_to_monitoring_sites(apps, schema_editor):
    MonitoringSite = apps.get_model("sta", "MonitoringSite")
    Location = apps.get_model("sta", "Location")

    locations = Location.objects.order_by("thing_id", "id")
    seen_site_ids = set()
    for location in locations.iterator():
        if location.thing_id in seen_site_ids:
            continue
        MonitoringSite.objects.filter(pk=location.thing_id).update(
            latitude=location.latitude,
            longitude=location.longitude,
            elevation_m=location.elevation_m,
            elevation_datum=location.elevation_datum,
            admin_area_1=location.admin_area_1,
            admin_area_2=location.admin_area_2,
            country=location.country,
        )
        seen_site_ids.add(location.thing_id)

    missing_location_site_ids = list(
        MonitoringSite.objects.filter(latitude__isnull=True)
        .order_by("id")
        .values_list("id", flat=True)[:10]
    )
    if missing_location_site_ids:
        missing_location_count = MonitoringSite.objects.filter(
            latitude__isnull=True
        ).count()
        raise RuntimeError(
            "Cannot merge Location into MonitoringSite because "
            f"{missing_location_count} monitoring site(s) have no Location. "
            "Create a Location for every site before retrying this migration. "
            f"Example site IDs: {', '.join(map(str, missing_location_site_ids))}"
        )


def restore_locations_from_monitoring_sites(apps, schema_editor):
    """
    Reverses copy_locations_to_monitoring_sites by creating one Location per
    MonitoringSite. This is lossy: any site that originally had more than one
    Location only gets one back, and the original Location ids are gone.
    name/description are copied from the site; encoding_type has no source
    field on MonitoringSite and is set to a placeholder.
    """

    MonitoringSite = apps.get_model("sta", "MonitoringSite")
    Location = apps.get_model("sta", "Location")

    Location.objects.bulk_create(
        [
            Location(
                thing_id=monitoring_site.id,
                name=monitoring_site.name,
                description=monitoring_site.description,
                encoding_type="application/geo+json",
                latitude=monitoring_site.latitude,
                longitude=monitoring_site.longitude,
                elevation_m=monitoring_site.elevation_m,
                elevation_datum=monitoring_site.elevation_datum,
                admin_area_1=monitoring_site.admin_area_1,
                admin_area_2=monitoring_site.admin_area_2,
                country=monitoring_site.country,
            )
            for monitoring_site in MonitoringSite.objects.all()
        ],
        batch_size=500,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("sta", "0011_alter_location_thing_alter_thingfileattachment_thing_and_more"),
        ("monitoring", "0001_initial"),
        ("products", "0002_alter_dataproducttransformation_aggregation_method"),
    ]

    operations = [
        migrations.RenameModel(old_name="Thing", new_name="MonitoringSite"),
        migrations.RenameModel(
            old_name="ThingTag", new_name="MonitoringSiteTag"
        ),
        migrations.RenameModel(
            old_name="ThingFileAttachment", new_name="MonitoringSiteFileAttachment"
        ),
        migrations.RenameField(
            model_name="monitoringsite",
            old_name="sampling_feature_code",
            new_name="code",
        ),
        migrations.RenameField(
            model_name="monitoringsite", old_name="site_type", new_name="type"
        ),
        migrations.AlterField(
            model_name="monitoringsite",
            name="sampling_feature_type",
            field=models.CharField(default="Site", max_length=200),
        ),
        migrations.RemoveField(
            model_name="monitoringsite", name="sampling_feature_type"
        ),
        migrations.RenameField(
            model_name="datastream", old_name="thing", new_name="monitoring_site"
        ),
        migrations.RenameField(
            model_name="monitoringsitetag",
            old_name="thing",
            new_name="monitoring_site",
        ),
        migrations.RenameField(
            model_name="monitoringsitefileattachment",
            old_name="thing",
            new_name="monitoring_site",
        ),
        migrations.AlterField(
            model_name="monitoringsite",
            name="workspace",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="monitoring_sites",
                to="iam.workspace",
            ),
        ),
        migrations.AlterField(
            model_name="monitoringsitetag",
            name="monitoring_site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="monitoring_site_tags",
                to="sta.monitoringsite",
            ),
        ),
        migrations.AlterField(
            model_name="monitoringsitefileattachment",
            name="monitoring_site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="monitoring_site_file_attachments",
                to="sta.monitoringsite",
            ),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="latitude",
            field=models.DecimalField(
                blank=True, decimal_places=16, max_digits=22, null=True
            ),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="longitude",
            field=models.DecimalField(
                blank=True, decimal_places=16, max_digits=22, null=True
            ),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="elevation_m",
            field=models.DecimalField(
                blank=True, decimal_places=16, max_digits=22, null=True
            ),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="elevation_datum",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="admin_area_1",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="admin_area_2",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="monitoringsite",
            name="country",
            field=models.CharField(blank=True, max_length=2, null=True),
        ),
        # Reversing this restores one placeholder Location per MonitoringSite;
        # the original Location ids and any extra per-site Location rows this
        # merge discarded are gone for good. See restore_locations_from_monitoring_sites.
        migrations.RunPython(
            copy_locations_to_monitoring_sites,
            reverse_code=restore_locations_from_monitoring_sites,
        ),
        migrations.AlterField(
            model_name="monitoringsite",
            name="latitude",
            field=models.DecimalField(decimal_places=16, max_digits=22),
        ),
        migrations.AlterField(
            model_name="monitoringsite",
            name="longitude",
            field=models.DecimalField(decimal_places=16, max_digits=22),
        ),
        migrations.AlterField(
            model_name="monitoringsitefileattachment",
            name="file_attachment",
            field=models.FileField(
                upload_to=core.sta.models.monitoring_site.monitoring_site_file_attachment_storage_path
            ),
        ),
        migrations.DeleteModel(name="Location"),
        migrations.DeleteModel(name="SamplingFeatureType"),
    ]
