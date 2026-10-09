"""
HydroServer v1.12 -> v2.0.0 schema and data migration for the iam app.

This is the first v2 migration to run, so it also holds the preflight checks for
every app's v1 data. If any check fails, nothing has been migrated yet and the
database is still a valid v1 database.

This migration is forward-only. Back up the database before applying it. See the
"Migrating from HydroServer v1 to v2" deployment guide for the manual data fixes this
migration requires and the data it drops or transforms.
"""

import core.iam.models.user
import django.contrib.postgres.indexes
import django.contrib.postgres.search
import django.db.models.deletion
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import migrations, models
from django.db.models import Count
from django.db.models.functions import Length


# v1 permission resource types that were renamed in v2.
RESOURCE_TYPE_RENAMES = {
    "APIKey": "ServiceAccount",
    "Thing": "MonitoringSite",
    "Sensor": "Method",
}

ACTION_FOR_PERMISSION_TYPE = {
    "view": "can_view",
    "create": "can_create",
    "edit": "can_edit",
    "delete": "can_delete",
}

API_KEY_PREFIX_LENGTH = 12


def _search_vector_trigger_sql(
    table: str,
    field_weights: dict[str, str],
    vector_column: str = "search_vector",
) -> list[migrations.RunSQL]:
    """
    Builds the migration operations needed to keep a `SearchVectorField` current via a
    Postgres trigger, plus a one-time backfill for existing rows.

    INSERT and UPDATE are handled by separate triggers rather than one combined
    `BEFORE INSERT OR UPDATE` trigger: the UPDATE trigger has a `WHEN` guard comparing
    OLD/NEW on only the source columns, so it skips recomputing the vector when a save
    touches unrelated columns. INSERT has no OLD row to compare against, so it always
    runs unconditionally.
    """

    function_name = f"{table}_{vector_column}_trigger"
    insert_trigger_name = f"{table}_{vector_column}_ins_trg"
    update_trigger_name = f"{table}_{vector_column}_upd_trg"

    new_expr = " || ".join(
        f"setweight(to_tsvector('english', coalesce(NEW.{field}, '')), '{weight}')"
        for field, weight in field_weights.items()
    )
    backfill_expr = " || ".join(
        f"setweight(to_tsvector('english', coalesce({field}, '')), '{weight}')"
        for field, weight in field_weights.items()
    )
    base_fields = dict.fromkeys(field.split("::", 1)[0] for field in field_weights)
    when_condition = " OR ".join(
        f"OLD.{field} IS DISTINCT FROM NEW.{field}" for field in base_fields
    )

    forward_sql = f"""
        CREATE OR REPLACE FUNCTION {function_name}() RETURNS trigger AS $$
        BEGIN
            NEW.{vector_column} := {new_expr};
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS {insert_trigger_name} ON {table};
        CREATE TRIGGER {insert_trigger_name}
        BEFORE INSERT ON {table}
        FOR EACH ROW EXECUTE FUNCTION {function_name}();

        DROP TRIGGER IF EXISTS {update_trigger_name} ON {table};
        CREATE TRIGGER {update_trigger_name}
        BEFORE UPDATE ON {table}
        FOR EACH ROW WHEN ({when_condition})
        EXECUTE FUNCTION {function_name}();

        UPDATE {table} SET {vector_column} = {backfill_expr};
    """

    return [migrations.RunSQL(sql=forward_sql)]


def _examples(values):
    values = list(values)
    return ", ".join(repr(str(value)) for value in values[:10])


def _is_url(value):
    try:
        URLValidator()(value)
    except ValidationError:
        return False
    return True


def _iam_problems(apps, alias):
    Role = apps.get_model("iam", "Role")
    APIKey = apps.get_model("iam", "APIKey")
    problems = []

    duplicate_global_roles = (
        Role.objects.using(alias)
        .filter(workspace__isnull=True)
        .values("name")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
        .order_by("name")
        .values_list("name", flat=True)
    )
    if duplicate_global_roles:
        problems.append(
            "iam_role.name: global roles (no workspace) must have unique names. "
            f"Duplicated names: {_examples(duplicate_global_roles)}"
        )

    duplicate_workspace_roles = list(
        Role.objects.using(alias)
        .filter(workspace__isnull=False)
        .values("workspace_id", "name")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
        .order_by("workspace_id", "name")
    )
    if duplicate_workspace_roles:
        problems.append(
            "iam_role.name: roles must have unique names within a workspace. "
            "Duplicated (workspace, name) pairs: "
            + _examples(
                f"{row['workspace_id']}: {row['name']}"
                for row in duplicate_workspace_roles
            )
        )

    malformed_keys = [
        api_key.id
        for api_key in APIKey.objects.using(alias).only("id", "hashed_key").order_by("id")
        if len(api_key.hashed_key.partition("$")[0]) != API_KEY_PREFIX_LENGTH
        or not api_key.hashed_key.partition("$")[2]
    ]
    if malformed_keys:
        problems.append(
            "iam_apikey.hashed_key: API keys must use the '<12-character prefix>$<hash>' "
            "format generated by HydroServer. Delete these API keys: "
            f"{_examples(malformed_keys)}"
        )

    return problems


def _sta_problems(apps, alias):
    problems = []

    def objects(model_name):
        return apps.get_model("sta", model_name).objects.using(alias)

    things_without_location = (
        objects("Thing")
        .exclude(id__in=objects("Location").values("thing_id"))
        .order_by("id")
        .values_list("id", flat=True)
    )
    if things_without_location:
        problems.append(
            "sta_location: every Thing must have a Location. Things without one: "
            f"{_examples(things_without_location)}"
        )

    for model_name, table, field, limit in [
        ("ObservedProperty", "sta_observedproperty", "code", 255),
        ("ObservedProperty", "sta_observedproperty", "observed_property_type", 255),
        ("ObservedProperty", "sta_observedproperty", "definition", 2000),
        ("Unit", "sta_unit", "definition", 2000),
    ]:
        oversized = (
            objects(model_name)
            .annotate(field_length=Length(field))
            .filter(field_length__gt=limit)
            .order_by("id")
            .values_list("id", flat=True)
        )
        if oversized:
            problems.append(
                f"{table}.{field}: values must be at most {limit} characters. "
                f"Rows over the limit: {_examples(oversized)}"
            )

    oversized_level_urls = [
        level.id
        for level in objects("ProcessingLevel").only("id", "definition").order_by("id")
        if len((level.definition or "").strip()) > 2000
        and _is_url((level.definition or "").strip())
    ]
    if oversized_level_urls:
        problems.append(
            "sta_processinglevel.definition: URL definitions must be at most 2000 "
            f"characters. Rows over the limit: {_examples(oversized_level_urls)}"
        )

    for model_name, table in [
        ("ThingFileAttachment", "sta_thingfileattachment"),
        ("DatastreamFileAttachment", "sta_datastreamfileattachment"),
    ]:
        missing_files = (
            objects(model_name)
            .filter(file_attachment="")
            .order_by("id")
            .values_list("id", flat=True)
        )
        if missing_files:
            problems.append(
                f"{table}.file_attachment: every file attachment must reference a file. "
                f"Attachments without one: {_examples(missing_files)}"
            )

    return problems


def _etl_problems(apps, alias):
    EtlMapping = apps.get_model("etl", "EtlMapping")
    PlaceholderVariable = apps.get_model("etl", "PlaceholderVariable")
    problems = []

    multiply_mapped_datastreams = (
        EtlMapping.objects.using(alias)
        .values("target_datastream_id")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
        .order_by("target_datastream_id")
        .values_list("target_datastream_id", flat=True)
    )
    if multiply_mapped_datastreams:
        problems.append(
            "etl_etlmapping.target_datastream: a datastream can be the target of only one "
            "ETL mapping. Datastreams targeted by more than one: "
            f"{_examples(multiply_mapped_datastreams)}"
        )

    duplicate_variables = list(
        PlaceholderVariable.objects.using(alias)
        .values("data_connection_id", "name", "variable_type")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
        .order_by("data_connection_id", "name", "variable_type")
    )
    if duplicate_variables:
        problems.append(
            "etl_placeholdervariable.name: (name, variable type) pairs must be unique "
            "within a data connection. Duplicated (data connection, name, variable type): "
            + _examples(
                f"{row['data_connection_id']}: {row['name']}, {row['variable_type']}"
                for row in duplicate_variables
            )
        )

    return problems


def _products_problems(apps, alias):
    RatingCurvePoint = apps.get_model("products", "RatingCurvePoint")
    duplicate_points = list(
        RatingCurvePoint.objects.using(alias)
        .values("rating_curve_id", "input_value")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
        .order_by("rating_curve_id", "input_value")
    )
    if not duplicate_points:
        return []
    return [
        "products_ratingcurvepoint.input_value: input values must be unique within a "
        "rating curve. Duplicated (rating curve, input value) pairs: "
        + _examples(
            f"{row['rating_curve_id']}: {row['input_value']}" for row in duplicate_points
        )
    ]


def preflight_checks(apps, schema_editor):
    """
    Reports every v1 data problem that would block the v2 migrations, across all apps,
    in one error before any changes are made.
    """

    alias = schema_editor.connection.alias
    problems = [
        *_iam_problems(apps, alias),
        *_sta_problems(apps, alias),
        *_etl_problems(apps, alias),
        *_products_problems(apps, alias),
    ]
    if problems:
        raise RuntimeError(
            "The HydroServer v2 migrations cannot run until the following v1 data "
            "problems are fixed. None of the HydroServer v2 migrations have been applied.\n  - "
            + "\n  - ".join(problems)
        )


def populate_service_account_keys(apps, schema_editor):
    """
    Splits the v1 '<prefix>$<hash>' key format into key_prefix and key_hash, and
    derives each service account's unique email from its key prefix.
    """

    ServiceAccount = apps.get_model("iam", "ServiceAccount")
    domain = getattr(settings, "SERVICE_ACCOUNT_EMAIL_DOMAIN", "hydroserver.local")
    for account in ServiceAccount.objects.all():
        prefix, _, key_hash = account.key_hash.partition("$")
        account.key_prefix = prefix
        account.key_hash = key_hash
        account.email = f"{prefix}@service-accounts.{domain}"
        account.save(update_fields=["key_prefix", "key_hash", "email"])
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def create_service_account_collaborators(apps, schema_editor):
    """
    v1 API keys held a role directly; v2 service accounts get workspace access
    through a Collaborator record like users do.
    """

    ServiceAccount = apps.get_model("iam", "ServiceAccount")
    Collaborator = apps.get_model("iam", "Collaborator")
    Collaborator.objects.bulk_create(
        [
            Collaborator(
                workspace_id=account.workspace_id,
                service_account_id=account.id,
                role_id=account.role_id,
            )
            for account in ServiceAccount.objects.all()
        ]
    )
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def consolidate_permissions(apps, schema_editor):
    """
    Collapses v1 permission_type rows into per-action boolean flags, applying v2
    resource type renames, so each (role, resource_type) pair has exactly one row.
    Duplicate rows are merged by OR-ing their granted actions, so no grant is lost.
    """

    Permission = apps.get_model("iam", "Permission")
    alias = schema_editor.connection.alias

    kept_by_key = {}
    stale_ids = []

    for permission in Permission.objects.using(alias).order_by("id"):
        resource_type = RESOURCE_TYPE_RENAMES.get(
            permission.resource_type, permission.resource_type
        )
        key = (permission.role_id, resource_type)

        if permission.permission_type == "*":
            flags = {field: True for field in ACTION_FOR_PERMISSION_TYPE.values()}
        else:
            flags = {
                field: permission.permission_type == action
                for action, field in ACTION_FOR_PERMISSION_TYPE.items()
            }

        kept = kept_by_key.get(key)
        if kept is None:
            permission.resource_type = resource_type
            for field, value in flags.items():
                setattr(permission, field, value)
            kept_by_key[key] = permission
        else:
            for field, value in flags.items():
                if value:
                    setattr(kept, field, True)
            stale_ids.append(permission.pk)

    for permission in kept_by_key.values():
        permission.save(
            update_fields=[
                "resource_type",
                "can_view",
                "can_create",
                "can_edit",
                "can_delete",
            ]
        )

    if stale_ids:
        Permission.objects.using(alias).filter(pk__in=stale_ids).delete()


def translate_ownership_policy(apps, schema_editor):
    """
    Preserves each user's v1 is_ownership_allowed flag (and superuser status, which
    always implied unlimited ownership) as owned_workspace_limit: unlimited (NULL)
    or 0.
    """

    User = apps.get_model("iam", "User")
    alias = schema_editor.connection.alias

    User.objects.using(alias).filter(
        models.Q(is_superuser=True) | models.Q(is_ownership_allowed=True)
    ).update(owned_workspace_limit=None)

    User.objects.using(alias).filter(
        is_superuser=False, is_ownership_allowed=False
    ).update(owned_workspace_limit=0)


class Migration(migrations.Migration):

    # The v1 leaves of the other apps are listed so that preflight_checks can read
    # their v1 data before any v2 migration changes it.
    dependencies = [
        ("iam", "0005_alter_permission_resource_type"),
        ("sta", "0008_remove_observation_result_qualifiers_and_more"),
        ("etl", "0009_payload_data_ingestion_window_end_anchor_and_more"),
        ("products", "0003_remove_dataproducttransformation_max_gap_interval_and_more"),
    ]

    operations = [
        migrations.RunPython(preflight_checks),

        # --- APIKey -> ServiceAccount -------------------------------------------------
        migrations.RenameModel(old_name="APIKey", new_name="ServiceAccount"),
        migrations.AlterModelOptions(
            name="serviceaccount",
            options={"verbose_name": "Service Account", "verbose_name_plural": "Service Accounts"},
        ),
        migrations.RenameField(model_name="serviceaccount", old_name="expires_at", new_name="key_expires_at"),
        migrations.RenameField(model_name="serviceaccount", old_name="last_used", new_name="last_used_at"),
        migrations.RenameField(model_name="serviceaccount", old_name="hashed_key", new_name="key_hash"),
        migrations.AddField(
            model_name="serviceaccount",
            name="key_prefix",
            field=models.CharField(default="", editable=False, max_length=12),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="serviceaccount",
            name="email",
            field=models.EmailField(blank=True, default="", editable=False, max_length=254),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="serviceaccount",
            name="key_created_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="serviceaccount",
            name="deactivated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(populate_service_account_keys),
        migrations.AlterField(
            model_name="serviceaccount",
            name="key_prefix",
            field=models.CharField(editable=False, max_length=12, unique=True),
        ),
        migrations.AlterField(
            model_name="serviceaccount",
            name="key_hash",
            field=models.CharField(blank=True, editable=False, max_length=128),
        ),
        migrations.AlterField(
            model_name="serviceaccount",
            name="email",
            field=models.EmailField(blank=True, editable=False, max_length=254, unique=True),
        ),
        migrations.AlterField(
            model_name="serviceaccount",
            name="workspace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="service_accounts",
                to="iam.workspace",
            ),
        ),

        # --- Collaborator: users or service accounts ----------------------------------
        migrations.AlterModelOptions(
            name="collaborator",
            options={"verbose_name": "Collaborator", "verbose_name_plural": "Collaborators"},
        ),
        migrations.AlterUniqueTogether(name="collaborator", unique_together=set()),
        migrations.AddField(
            model_name="collaborator",
            name="service_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="collaborations",
                to="iam.serviceaccount",
            ),
        ),
        migrations.AlterField(
            model_name="collaborator",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="collaborations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(create_service_account_collaborators),
        migrations.RemoveField(model_name="serviceaccount", name="role"),
        migrations.AlterField(
            model_name="collaborator",
            name="role",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="collaborator_assignments",
                to="iam.role",
            ),
        ),
        migrations.AlterField(
            model_name="collaborator",
            name="workspace",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="collaborators",
                to="iam.workspace",
            ),
        ),
        migrations.AddConstraint(
            model_name="collaborator",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("service_account__isnull", True), ("user__isnull", False)),
                    models.Q(("service_account__isnull", False), ("user__isnull", True)),
                    _connector="OR",
                ),
                name="collaborator_principal_is_user_xor_service_account",
            ),
        ),
        migrations.AddConstraint(
            model_name="collaborator",
            constraint=models.UniqueConstraint(
                condition=models.Q(("user__isnull", False)),
                fields=("workspace", "user"),
                name="unique_workspace_user_collaborator",
                violation_error_message="This account already collaborates on the workspace",
            ),
        ),
        migrations.AddConstraint(
            model_name="collaborator",
            constraint=models.UniqueConstraint(
                condition=models.Q(("service_account__isnull", False)),
                fields=("workspace", "service_account"),
                name="unique_workspace_service_account_collaborator",
                violation_error_message="This account already collaborates on the workspace",
            ),
        ),

        # --- Permission: per-action flags ---------------------------------------------
        migrations.AddField(
            model_name="permission",
            name="can_create",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="permission",
            name="can_delete",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="permission",
            name="can_edit",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="permission",
            name="can_view",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(consolidate_permissions),
        migrations.RemoveField(model_name="permission", name="permission_type"),
        migrations.AlterField(
            model_name="permission",
            name="resource_type",
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name="permission",
            name="role",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="permissions",
                to="iam.role",
            ),
        ),
        migrations.AddConstraint(
            model_name="permission",
            constraint=models.UniqueConstraint(
                fields=("role", "resource_type"), name="unique_role_resource_type"
            ),
        ),

        # --- Role ---------------------------------------------------------------------
        migrations.RemoveField(model_name="role", name="is_apikey_role"),
        migrations.RemoveField(model_name="role", name="is_user_role"),
        migrations.AlterField(
            model_name="role",
            name="workspace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="roles",
                to="iam.workspace",
            ),
        ),
        migrations.AddConstraint(
            model_name="role",
            constraint=models.UniqueConstraint(
                condition=models.Q(("workspace__isnull", True)),
                fields=("name",),
                name="unique_global_role_name",
            ),
        ),
        migrations.AddConstraint(
            model_name="role",
            constraint=models.UniqueConstraint(
                condition=models.Q(("workspace__isnull", False)),
                fields=("workspace", "name"),
                name="unique_workspace_role_name",
            ),
        ),

        # --- User: ownership limit ----------------------------------------------------
        migrations.AlterModelManagers(
            name="user",
            managers=[
                ("objects", core.iam.models.user.UserManager()),
            ],
        ),
        migrations.AddField(
            model_name="user",
            name="owned_workspace_limit",
            field=models.PositiveSmallIntegerField(blank=True, default=1, null=True),
        ),
        migrations.RunPython(translate_ownership_policy),
        migrations.RemoveField(model_name="user", name="is_ownership_allowed"),

        # --- Workspace ----------------------------------------------------------------
        migrations.DeleteModel(name="WorkspaceDeleteConfirmation"),
        migrations.RemoveField(model_name="workspacetransferconfirmation", name="initiated"),
        migrations.AlterField(
            model_name="workspace",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="owned_workspaces",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="search_vector",
            field=django.contrib.postgres.search.SearchVectorField(editable=False, null=True),
        ),
        *_search_vector_trigger_sql("iam_workspace", {"name": "A"}),
        migrations.AddIndex(
            model_name="workspace",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["search_vector"], name="iam_workspace_search_gin"
            ),
        ),
    ]
