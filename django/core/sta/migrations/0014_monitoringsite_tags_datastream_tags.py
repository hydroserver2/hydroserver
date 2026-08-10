from django.contrib.postgres.indexes import GinIndex
from django.db import migrations, models
from django.db.models import Q


def migrate_monitoring_site_tags(_apps, schema_editor):
    schema_editor.execute("""
        UPDATE sta_monitoringsite
        SET tags = COALESCE(subq.tags, '{}'::jsonb)
        FROM (
            SELECT monitoring_site_id, jsonb_object_agg(key, value ORDER BY id ASC) AS tags
            FROM sta_monitoringsitetag
            GROUP BY monitoring_site_id
        ) AS subq
        WHERE sta_monitoringsite.id = subq.monitoring_site_id
    """)


def reverse_migrate_monitoring_site_tags(_apps, schema_editor):
    schema_editor.execute("""
        INSERT INTO sta_monitoringsitetag (monitoring_site_id, key, value)
        SELECT ms.id, kv.key, kv.value
        FROM sta_monitoringsite ms,
        LATERAL jsonb_each_text(ms.tags) AS kv(key, value)
        WHERE ms.tags IS NOT NULL AND ms.tags != '{}'::jsonb
    """)


def migrate_datastream_tags(_apps, schema_editor):
    schema_editor.execute("""
        UPDATE sta_datastream
        SET tags = COALESCE(subq.tags, '{}'::jsonb)
        FROM (
            SELECT datastream_id, jsonb_object_agg(key, value ORDER BY id ASC) AS tags
            FROM sta_datastreamtag
            GROUP BY datastream_id
        ) AS subq
        WHERE sta_datastream.id = subq.datastream_id
    """)


def reverse_migrate_datastream_tags(_apps, schema_editor):
    schema_editor.execute("""
        INSERT INTO sta_datastreamtag (datastream_id, key, value)
        SELECT d.id, kv.key, kv.value
        FROM sta_datastream d,
        LATERAL jsonb_each_text(d.tags) AS kv(key, value)
        WHERE d.tags IS NOT NULL AND d.tags != '{}'::jsonb
    """)


class Migration(migrations.Migration):

    dependencies = [
        ("sta", "0013_rename_sensor_method"),
    ]

    operations = [
        migrations.AddField(
            model_name="monitoringsite",
            name="tags",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="datastream",
            name="tags",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(migrate_monitoring_site_tags, reverse_migrate_monitoring_site_tags),
        migrations.RunPython(migrate_datastream_tags, reverse_migrate_datastream_tags),
        migrations.AddIndex(
            model_name="monitoringsite",
            index=GinIndex(
                fields=["tags"],
                name="sta_monitoringsite_tags_gin",
                opclasses=["jsonb_path_ops"],
                condition=~Q(tags={}),
            ),
        ),
        migrations.AddIndex(
            model_name="datastream",
            index=GinIndex(
                fields=["tags"],
                name="sta_datastream_tags_gin",
                opclasses=["jsonb_path_ops"],
                condition=~Q(tags={}),
            ),
        ),
        migrations.DeleteModel(name="MonitoringSiteTag"),
        migrations.DeleteModel(name="DatastreamTag"),
    ]