"""
Custom migration that restructures the old etl.Task model into two separate concerns:

  - orchestration.Task — generic schedulable unit (preserves original UUID)
  - orchestration.TaskRun — generic run history
  - etl.EtlTask — ETL-specific task linked to a DataConnection

ETL variable fields (extractor_variables, transformer_variables, loader_variables) are
merged into EtlTask.runtime_variables. The data_transformations field is not migrated.

Tasks with task_type="Aggregation" are not auto-migrated — the migration aborts if any
exist. Those records must be manually converted to DataProductTask before running this
migration.

Pre-migration checks (non-INTERNAL OrchestrationSystems, unsupported task types) run
at the start of migrate_tasks_forward. The entire migration runs in a single transaction,
so any failure rolls back all schema changes.

This migration is reversible. Note: the original OrchestrationSystem data is not
recoverable on reverse — restored Task records are assigned a placeholder INTERNAL system.
"""

import uuid6
import django.db.models.deletion
from django.db import migrations, models


def cleanup_etl_notification_schedules_reverse(apps, schema_editor):
    """
    Reverse-only cleanup: delete PeriodicTask rows (and their crontab/interval
    schedules) that are linked to DataConnectionNotification records before the
    table is dropped. Without this, those PeriodicTask rows would be permanently
    orphaned because the schema drop does not cascade to django_celery_beat tables.
    """
    DataConnectionNotification = apps.get_model("etl", "DataConnectionNotification")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")

    for notification in DataConnectionNotification.objects.select_related("periodic_task").all():
        pt = notification.periodic_task
        if not pt:
            continue

        if pt.crontab_id:
            crontab_id = pt.crontab_id
            PeriodicTask.objects.filter(pk=pt.pk).update(crontab=None)
            CrontabSchedule.objects.filter(pk=crontab_id).delete()

        if pt.interval_id:
            interval_id = pt.interval_id
            PeriodicTask.objects.filter(pk=pt.pk).update(interval=None)
            IntervalSchedule.objects.filter(pk=interval_id).delete()

        DataConnectionNotification.objects.filter(pk=notification.pk).update(periodic_task=None)
        pt.delete()


ALLOWED_TASK_TYPES = {"ETL"}
VALID_STATUSES = {"PENDING", "STARTED", "SUCCESS", "FAILURE"}

TIMEZONE_MODE_MAP = {
    "daylightSavings": "iana",
    "fixedOffset": "offset",
    "utc": "utc",
    "UTC": "utc",
}

REVERSE_TIMEZONE_MODE_MAP = {
    "iana": "daylightSavings",
    "offset": "fixedOffset",
    "utc": "UTC",
}


def migrate_tasks_forward(apps, schema_editor):
    OldTask = apps.get_model("etl", "Task")
    OldTaskRun = apps.get_model("etl", "TaskRun")
    OldTaskMapping = apps.get_model("etl", "TaskMapping")
    OldTaskMappingPath = apps.get_model("etl", "TaskMappingPath")
    EtlTask = apps.get_model("etl", "EtlTask")
    EtlMapping = apps.get_model("etl", "EtlMapping")
    OrcTask = apps.get_model("orchestration", "Task")
    OrcTaskRun = apps.get_model("orchestration", "TaskRun")
    OrchestrationSystem = apps.get_model("etl", "OrchestrationSystem")
    DataConnection = apps.get_model("etl", "DataConnection")
    Payload = apps.get_model("etl", "Payload")
    PlaceholderVariable = apps.get_model("etl", "PlaceholderVariable")
    Datastream = apps.get_model("sta", "Datastream")

    # Halt if any non-INTERNAL orchestration systems exist
    non_internal = list(
        OrchestrationSystem.objects
        .exclude(orchestration_system_type="INTERNAL")
        .values_list("orchestration_system_type", flat=True)
        .distinct()
    )
    if non_internal:
        raise Exception(
            f"Migration aborted: non-INTERNAL orchestration system type(s) exist: {non_internal}. "
            "Remove or convert these before migrating."
        )

    # Halt if any DataConnections are missing a workspace
    orphaned_connections = DataConnection.objects.filter(workspace__isnull=True).count()
    if orphaned_connections:
        raise Exception(
            f"Migration aborted: {orphaned_connections} DataConnection(s) have no workspace. "
            "Assign a workspace to all DataConnections before migrating."
        )

    # Validate all task types before making any changes
    unknown_types = list(
        OldTask.objects
        .exclude(task_type__in=list(ALLOWED_TASK_TYPES))
        .values_list("task_type", flat=True)
        .distinct()
    )
    if unknown_types:
        raise Exception(
            f"Migration aborted: tasks exist with unsupported task_type(s): {unknown_types}. "
            "Only 'ETL' is supported. Resolve these before migrating."
        )

    # Migrate DataConnection fields from old JSON settings to dedicated fields,
    # and create Payload and PlaceholderVariable records.
    for dc in DataConnection.objects.all():
        extractor_settings = dc.extractor_settings or {}
        transformer_settings = dc.transformer_settings or {}
        timestamp = transformer_settings.get("timestamp") or {}

        dc.source_url = extractor_settings.get("sourceUri", "")
        dc.timestamp_key = timestamp.get("key", "")
        dc.timestamp_format = timestamp.get("format")
        dc.timezone = timestamp.get("timezone")
        dc.timezone_type = TIMEZONE_MODE_MAP.get(timestamp.get("timezoneMode", ""))
        dc.save(update_fields=["source_url", "timestamp_key", "timestamp_format", "timezone", "timezone_type"])

        for pv in extractor_settings.get("placeholderVariables", []):
            PlaceholderVariable.objects.create(
                data_connection=dc,
                name=pv.get("name", ""),
                variable_type=pv.get("type", ""),
            )

        transformer_type = (dc.transformer_type or "").upper()
        if transformer_type == "CSV":
            Payload.objects.create(
                data_connection=dc,
                payload_type="CSV",
                header_row=transformer_settings.get("headerRow"),
                data_start_row=transformer_settings.get("dataStartRow"),
                delimiter=transformer_settings.get("delimiter"),
            )
        elif transformer_type == "JSON":
            Payload.objects.create(
                data_connection=dc,
                payload_type="JSON",
                jmespath=transformer_settings.get("JMESPath"),
            )

    for old_task in OldTask.objects.select_related("data_connection", "periodic_task").all():
        periodic_task = old_task.periodic_task

        # Detach periodic_task from old ETL task before linking to orchestration.Task.
        # Both models have a OneToOneField to PeriodicTask in different DB columns,
        # so the old column must be cleared first.
        if periodic_task:
            OldTask.objects.filter(id=old_task.id).update(periodic_task=None)

        # Create orchestration.Task preserving the original UUID so existing
        # PeriodicTask kwargs ({"task_id": "..."}) remain valid without update.
        orc_task = OrcTask.objects.create(
            id=old_task.id,
            name=old_task.name,
            next_run_at=old_task.next_run_at,
            periodic_task_id=periodic_task.id if periodic_task else None,
        )

        # Migrate task runs, preserving original started_at via update() to bypass
        # auto_now_add on the new model.
        for old_run in OldTaskRun.objects.filter(task_id=old_task.id):
            status = old_run.status if old_run.status in VALID_STATUSES else "SUCCESS"
            new_run = OrcTaskRun.objects.create(
                task_id=orc_task.id,
                status=status,
                finished_at=old_run.finished_at,
                result=old_run.result,
            )
            OrcTaskRun.objects.filter(id=new_run.id).update(started_at=old_run.started_at)

        if old_task.task_type == "ETL":
            import json as _json
            runtime_variables = {
                **(old_task.extractor_variables or {}),
                **(old_task.transformer_variables or {}),
                **(old_task.loader_variables or {}),
            }
            # Insert directly into the child table to avoid Django's MTI save()
            # trying to re-INSERT/UPDATE the already-created parent Task row.
            with schema_editor.connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO etl_etltask (task_ptr_id, data_connection_id, runtime_variables) "
                    "VALUES (%s, %s, %s)",
                    [str(orc_task.pk), str(old_task.data_connection_id), _json.dumps(runtime_variables)],
                )
            etl_task = EtlTask.objects.get(pk=orc_task.pk)

            # Flatten TaskMapping + TaskMappingPath into EtlMapping.
            # data_transformations are intentionally not migrated.
            for old_mapping in OldTaskMapping.objects.filter(task_id=old_task.id):
                for old_path in OldTaskMappingPath.objects.filter(task_mapping_id=old_mapping.id):
                    try:
                        target_ds = Datastream.objects.get(id=old_path.target_identifier)
                    except Datastream.DoesNotExist:
                        continue
                    EtlMapping.objects.create(
                        etl_task_id=etl_task.pk,
                        source_identifier=old_mapping.source_identifier,
                        target_datastream_id=target_ds.id,
                    )


def migrate_tasks_reverse(apps, schema_editor):
    OldTask = apps.get_model("etl", "Task")
    OldTaskRun = apps.get_model("etl", "TaskRun")
    OldTaskMapping = apps.get_model("etl", "TaskMapping")
    OldTaskMappingPath = apps.get_model("etl", "TaskMappingPath")
    EtlTask = apps.get_model("etl", "EtlTask")
    EtlMapping = apps.get_model("etl", "EtlMapping")
    OrcTask = apps.get_model("orchestration", "Task")
    OrcTaskRun = apps.get_model("orchestration", "TaskRun")
    OrchestrationSystem = apps.get_model("etl", "OrchestrationSystem")
    DataConnection = apps.get_model("etl", "DataConnection")
    Payload = apps.get_model("etl", "Payload")
    PlaceholderVariable = apps.get_model("etl", "PlaceholderVariable")

    # orchestration_system is non-nullable on the old Task model. The original
    # OrchestrationSystem data was deleted in the forward migration and cannot be
    # recovered, so a placeholder INTERNAL system is created to satisfy the constraint.
    placeholder_orc_system = OrchestrationSystem.objects.create(
        name="Restored",
        orchestration_system_type="INTERNAL",
    )

    migrated_task_ids = set()

    # Restore ETL tasks
    for etl_task in EtlTask.objects.select_related("data_connection").all():
        periodic_task = etl_task.periodic_task
        migrated_task_ids.add(etl_task.pk)

        if periodic_task:
            OrcTask.objects.filter(id=etl_task.pk).update(periodic_task=None)

        old_task = OldTask.objects.create(
            id=etl_task.pk,
            name=etl_task.name,
            task_type="ETL",
            workspace_id=etl_task.data_connection.workspace_id,
            data_connection_id=etl_task.data_connection_id,
            orchestration_system_id=placeholder_orc_system.id,
            next_run_at=etl_task.next_run_at,
            paused=(not periodic_task.enabled) if periodic_task else False,
            periodic_task_id=periodic_task.id if periodic_task else None,
            extractor_variables=etl_task.runtime_variables or {},
            transformer_variables={},
            loader_variables={},
        )

        for orc_run in OrcTaskRun.objects.filter(task_id=etl_task.pk):
            old_run = OldTaskRun.objects.create(
                task_id=old_task.id,
                status=orc_run.status,
                finished_at=orc_run.finished_at,
                result=orc_run.result,
            )
            OldTaskRun.objects.filter(id=old_run.id).update(started_at=orc_run.started_at)

        # Re-group EtlMappings back into TaskMapping + TaskMappingPath structure
        mapping_groups = {}
        for etl_mapping in EtlMapping.objects.filter(etl_task_id=etl_task.pk):
            source_id = etl_mapping.source_identifier
            if source_id not in mapping_groups:
                mapping_groups[source_id] = OldTaskMapping.objects.create(
                    task_id=old_task.id,
                    source_identifier=source_id,
                )
            OldTaskMappingPath.objects.create(
                task_mapping_id=mapping_groups[source_id].id,
                target_identifier=str(etl_mapping.target_datastream_id),
                data_transformations=[],
            )

    # Reconstruct old DataConnection JSON settings from dedicated fields and
    # Payload/PlaceholderVariable records before those tables are dropped.
    for dc in DataConnection.objects.prefetch_related("placeholder_variables").all():
        timezone_mode = REVERSE_TIMEZONE_MODE_MAP.get(dc.timezone_type or "", "")
        timestamp = {"key": dc.timestamp_key or ""}
        if dc.timestamp_format:
            timestamp["format"] = dc.timestamp_format
        if timezone_mode:
            timestamp["timezoneMode"] = timezone_mode
        if dc.timezone:
            timestamp["timezone"] = dc.timezone

        placeholder_variables = [
            {"name": pv.name, "type": pv.variable_type, "runTimeValue": ""}
            for pv in dc.placeholder_variables.all()
        ]
        extractor_settings = {"sourceUri": dc.source_url or ""}
        if placeholder_variables:
            extractor_settings["placeholderVariables"] = placeholder_variables

        transformer_settings = {"timestamp": timestamp}
        try:
            payload = dc.payload
            if payload.payload_type == "CSV":
                if payload.delimiter is not None:
                    transformer_settings["delimiter"] = payload.delimiter
                if payload.header_row is not None:
                    transformer_settings["headerRow"] = payload.header_row
                if payload.data_start_row is not None:
                    transformer_settings["dataStartRow"] = payload.data_start_row
                transformer_type = "CSV"
            elif payload.payload_type == "JSON":
                if payload.jmespath:
                    transformer_settings["JMESPath"] = payload.jmespath
                transformer_type = "JSON"
            else:
                transformer_type = ""
        except Payload.DoesNotExist:
            transformer_type = ""

        DataConnection.objects.filter(id=dc.id).update(
            extractor_settings=extractor_settings,
            transformer_type=transformer_type,
            transformer_settings=transformer_settings,
            loader_settings={},
        )

    # Clean up orchestration data.
    # EtlTask uses MTI (CASCADE parent link), so deleting it also removes the parent Task rows.
    OrcTaskRun.objects.filter(task_id__in=migrated_task_ids).delete()
    EtlTask.objects.filter(pk__in=migrated_task_ids).delete()
    OrcTask.objects.filter(id__in=migrated_task_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("django_celery_beat", "0019_alter_periodictasks_options"),
        ("etl", "0007_dataconnectionnotificationrecipient"),
        ("iam", "0004_alter_permission_resource_type"),
        ("orchestration", "0001_initial"),
        ("sta", "0007_remove_thingfileattachment_download_token_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name='Payload',
            fields=[
                ('id', models.UUIDField(default=uuid6.uuid7, editable=False, primary_key=True, serialize=False)),
                ('payload_type', models.CharField(choices=[('CSV', 'Csv'), ('JSON', 'Json')], max_length=255)),
                ('header_row', models.IntegerField(blank=True, null=True)),
                ('data_start_row', models.IntegerField(blank=True, null=True)),
                ('delimiter', models.CharField(blank=True, max_length=1, null=True)),
                ('jmespath', models.TextField(blank=True, null=True)),
                ('data_connection',
                 models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payload',
                                      to='etl.dataconnection')),
            ],
        ),
        migrations.CreateModel(
            name='PlaceholderVariable',
            fields=[
                ('id', models.UUIDField(default=uuid6.uuid7, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('variable_type', models.CharField(max_length=255)),
                ('data_connection',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='placeholder_variables',
                                   to='etl.dataconnection')),
            ],
        ),
        migrations.CreateModel(
            name="EtlTask",
            fields=[
                (
                    "task_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="orchestration.task",
                    ),
                ),
                ("runtime_variables", models.JSONField(default=dict)),
                ("data_connection", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="etl_tasks",
                    to="etl.dataconnection",
                )),
            ],
            bases=("orchestration.task",),
        ),
        migrations.CreateModel(
            name="EtlMapping",
            fields=[
                ("id", models.UUIDField(default=uuid6.uuid7, editable=False, primary_key=True, serialize=False)),
                ("source_identifier", models.CharField(max_length=255)),
                ("etl_task", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="etl_mappings",
                    to="etl.etltask",
                )),
                ("target_datastream", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="etl_mappings",
                    to="sta.datastream",
                )),
            ],
        ),

        # Add new fields to data connection model
        migrations.AddField(
            model_name='dataconnection',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dataconnection',
            name='source_url',
            field=models.URLField(default='http://www.example.com'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='dataconnection',
            name='timestamp_format',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='dataconnection',
            name='timestamp_key',
            field=models.CharField(default='TIMESTAMP', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='dataconnection',
            name='timezone',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='dataconnection',
            name='timezone_type',
            field=models.CharField(blank=True, choices=[('utc', 'Utc'), ('offset', 'Offset'), ('iana', 'Iana')],
                                   max_length=255, null=True),
        ),

        # Migrate data from old tables to new structure
        migrations.RunPython(migrate_tasks_forward, migrate_tasks_reverse),

        # Alter fields on existing models
        migrations.AlterField(
            model_name='dataconnection',
            name='workspace',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='data_connections',
                                    to='iam.workspace'),
        ),
        migrations.AlterField(
            model_name='dataconnection',
            name='data_connection_type',
            field=models.CharField(max_length=255, null=True, default='ETL'),
        ),
        migrations.RemoveField(
            model_name='dataconnection',
            name='data_connection_type',
        ),
        migrations.RemoveField(
            model_name='dataconnection',
            name='extractor_settings',
        ),
        migrations.RemoveField(
            model_name='dataconnection',
            name='extractor_type',
        ),
        migrations.RemoveField(
            model_name='dataconnection',
            name='loader_settings',
        ),
        migrations.RemoveField(
            model_name='dataconnection',
            name='loader_type',
        ),
        migrations.RemoveField(
            model_name='dataconnection',
            name='transformer_settings',
        ),
        migrations.RemoveField(
            model_name='dataconnection',
            name='transformer_type',
        ),

        # Remove orchestration_system FK from Task before dropping both tables.
        # This ensures Django's migration state records Task without the field,
        # so the reverse can recreate OldTask records without providing it.
        migrations.RemoveField(model_name="task", name="orchestration_system"),

        # Drop old tables
        migrations.DeleteModel(name="TaskMappingPath"),
        migrations.DeleteModel(name="TaskMapping"),
        migrations.DeleteModel(name="TaskRun"),
        migrations.DeleteModel(name="Task"),
        migrations.DeleteModel(name="OrchestrationSystem"),
        migrations.DeleteModel(name="DataConnectionNotificationRecipient"),

        migrations.CreateModel(
            name='DataConnectionNotification',
            fields=[
                ('data_connection', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    primary_key=True,
                    related_name='notification',
                    serialize=False,
                    to='etl.dataconnection',
                )),
                ('periodic_task', models.OneToOneField(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='data_connection_notification',
                    to='django_celery_beat.periodictask',
                )),
            ],
            options={'app_label': 'etl'},
        ),
        migrations.CreateModel(
            name='DataConnectionNotificationRecipient',
            fields=[
                ('id', models.UUIDField(default=uuid6.uuid7, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(max_length=254)),
                ('notification', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='recipients',
                    to='etl.dataconnectionnotification',
                )),
            ],
            options={
                'app_label': 'etl',
                'constraints': [
                    models.UniqueConstraint(
                        fields=('notification', 'email'),
                        name='unique_data_connection_notification_recipient_email',
                    )
                ],
            },
        ),

        # Reverse-only: clean up PeriodicTask rows linked to DataConnectionNotification
        # before the table is dropped. Runs as the first step on reverse (last in forward).
        migrations.RunPython(
            migrations.RunPython.noop,
            cleanup_etl_notification_schedules_reverse,
        ),
    ]
