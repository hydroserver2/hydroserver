"""
Tests for the HydroServer v1.12 -> v2.0.0 data migrations.

The v2 migrations are forward-only, so these tests can't migrate the test database
backwards. Each test rebuilds the schema, migrates forward to the v1.12 leaves, seeds
v1 data through the historical models, then migrates forward to the latest leaves.
"""

from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


V1_LEAVES = [
    ("iam", "0005_alter_permission_resource_type"),
    ("sta", "0008_remove_observation_result_qualifiers_and_more"),
    ("etl", "0009_payload_data_ingestion_window_end_anchor_and_more"),
    ("monitoring", "0001_initial"),
    ("orchestration", "0001_initial"),
    ("products", "0003_remove_dataproducttransformation_max_gap_interval_and_more"),
    ("quality", "0002_qcoperation_created_by"),
    ("web", "0003_google_analytics"),
]


def _reset_schema():
    with connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")


def _migrate(targets=None):
    executor = MigrationExecutor(connection)
    targets = targets or executor.loader.graph.leaf_nodes()
    executor.migrate(targets)
    return MigrationExecutor(connection).loader.project_state(targets).apps


@pytest.fixture
def v1_apps():
    _reset_schema()
    try:
        yield _migrate(V1_LEAVES)
    finally:
        # Leave the test database at the latest schema for the tests that follow.
        _reset_schema()
        _migrate()


def _seed_v1(apps):
    User = apps.get_model("iam", "User")
    Workspace = apps.get_model("iam", "Workspace")
    Role = apps.get_model("iam", "Role")
    Permission = apps.get_model("iam", "Permission")
    APIKey = apps.get_model("iam", "APIKey")
    Collaborator = apps.get_model("iam", "Collaborator")

    owner = User.objects.create(
        username="owner", email="owner@example.com", is_ownership_allowed=True
    )
    limited = User.objects.create(
        username="limited", email="limited@example.com", is_ownership_allowed=False
    )
    superuser = User.objects.create(
        username="admin", email="admin@example.com", is_superuser=True,
        is_ownership_allowed=False,
    )
    workspace = Workspace.objects.create(name="Workspace", owner=owner, is_private=False)

    role = Role.objects.create(name="Editor", workspace=workspace)
    key_role = Role.objects.create(name="Key Role", workspace=workspace, is_apikey_role=True)
    for permission_type, resource_type in [
        ("view", "Thing"), ("edit", "Thing"), ("delete", "Sensor"),
        ("view", "APIKey"), ("*", "Datastream"), ("view", "Datastream"),
    ]:
        Permission.objects.create(
            role=role, permission_type=permission_type, resource_type=resource_type
        )
    Permission.objects.create(role=key_role, permission_type="*", resource_type="*")
    Collaborator.objects.create(user=limited, workspace=workspace, role=role)
    api_key = APIKey.objects.create(
        name="Loader", workspace=workspace, role=key_role,
        hashed_key="AbCdEfGh1234$pbkdf2_sha256$600000$salt$hash",
    )

    Thing = apps.get_model("sta", "Thing")
    Location = apps.get_model("sta", "Location")
    ThingTag = apps.get_model("sta", "ThingTag")
    ProcessingLevel = apps.get_model("sta", "ProcessingLevel")
    ResultQualifier = apps.get_model("sta", "ResultQualifier")

    thing = Thing.objects.create(
        workspace=workspace, name="Site", description="desc", sampling_feature_type="Site",
        sampling_feature_code="S1", site_type="Stream",
    )
    for name, latitude in [("First", 41), ("Second", 10)]:
        Location.objects.create(
            thing=thing, name=name, description="d", encoding_type="application/geo+json",
            latitude=latitude, longitude=-111, country="US",
        )
    for key, value in [("basin", "Bear"), ("basin", "Logan"), ("owner", "usu")]:
        ThingTag.objects.create(thing=thing, key=key, value=value)

    levels = {
        "uri": ProcessingLevel.objects.create(
            code="1", definition="https://example.com/pl", explanation="Explained"
        ),
        "short": ProcessingLevel.objects.create(
            code="0", definition="Raw data", explanation="Not quality controlled"
        ),
        "empty": ProcessingLevel.objects.create(code="2", definition=None, explanation=None),
        "long": ProcessingLevel.objects.create(
            code="3", definition="L" * 300, explanation="Explained"
        ),
        "nameless": ProcessingLevel.objects.create(code="", definition="", explanation=""),
    }
    qualifier = ResultQualifier.objects.create(code="ICE", description="Ice affected")

    return {
        "owner": owner, "limited": limited, "superuser": superuser, "role": role,
        "key_role": key_role, "api_key": api_key, "thing": thing, "levels": levels,
        "qualifier": qualifier,
    }


@pytest.mark.django_db(transaction=True)
def test_v2_migration_transforms_v1_data(v1_apps):
    seeded = _seed_v1(v1_apps)

    apps = _migrate()

    User = apps.get_model("iam", "User")
    assert User.objects.get(pk=seeded["owner"].pk).owned_workspace_limit is None
    assert User.objects.get(pk=seeded["superuser"].pk).owned_workspace_limit is None
    assert User.objects.get(pk=seeded["limited"].pk).owned_workspace_limit == 0

    permissions = {
        permission.resource_type: (
            permission.can_view, permission.can_create, permission.can_edit, permission.can_delete
        )
        for permission in apps.get_model("iam", "Permission").objects.filter(role_id=seeded["role"].pk)
    }
    assert permissions == {
        "MonitoringSite": (True, False, True, False),
        "Method": (False, False, False, True),
        "ServiceAccount": (True, False, False, False),
        "Datastream": (True, True, True, True),
    }

    account = apps.get_model("iam", "ServiceAccount").objects.get(pk=seeded["api_key"].pk)
    assert account.key_prefix == "AbCdEfGh1234"
    assert account.key_hash == "pbkdf2_sha256$600000$salt$hash"
    assert account.email.startswith("AbCdEfGh1234@service-accounts.")
    collaborator = apps.get_model("iam", "Collaborator").objects.get(service_account=account)
    assert collaborator.role_id == seeded["key_role"].pk
    assert collaborator.user_id is None

    site = apps.get_model("sta", "MonitoringSite").objects.get(pk=seeded["thing"].pk)
    assert site.code == "S1"
    assert site.type == "Stream"
    assert site.latitude == Decimal(41)
    assert site.country == "US"
    assert site.tags == {"basin": "Logan", "owner": "usu"}

    ProcessingLevel = apps.get_model("sta", "ProcessingLevel")
    levels = {
        label: ProcessingLevel.objects.get(pk=level.pk)
        for label, level in seeded["levels"].items()
    }
    assert (levels["uri"].name, levels["uri"].definition, levels["uri"].description) == (
        "1", "https://example.com/pl", "Explained"
    )
    assert (levels["short"].name, levels["short"].definition, levels["short"].description) == (
        "Raw data", None, "Not quality controlled"
    )
    assert (levels["empty"].name, levels["empty"].definition, levels["empty"].description) == (
        "2", None, ""
    )
    assert (levels["long"].name, levels["long"].definition, levels["long"].description) == (
        "3", None, "L" * 300 + "\n\nExplained"
    )
    assert levels["nameless"].name == str(levels["nameless"].pk)

    qualifier = apps.get_model("sta", "ResultQualifier").objects.get(pk=seeded["qualifier"].pk)
    assert qualifier.name == "ICE"
    assert qualifier.description == "Ice affected"

    assert apps.get_model("sta", "MonitoringSite").objects.filter(search_vector="Site").exists()


@pytest.mark.django_db(transaction=True)
def test_v2_migration_preflight_blocks_without_changes(v1_apps):
    seeded = _seed_v1(v1_apps)
    Role = v1_apps.get_model("iam", "Role")
    Thing = v1_apps.get_model("sta", "Thing")
    duplicate_role = Role.objects.create(name="Editor", workspace_id=seeded["role"].workspace_id)
    siteless_thing = Thing.objects.create(
        workspace_id=seeded["thing"].workspace_id, name="No Location", description="d",
        sampling_feature_type="Site", sampling_feature_code="NL", site_type="Stream",
    )

    with pytest.raises(RuntimeError) as error:
        _migrate()

    message = str(error.value)
    assert "None of the HydroServer v2 migrations have been applied" in message
    assert "iam_role.name" in message
    assert f"sta_location: every Thing must have a Location. Things without one: '{siteless_thing.pk}'" in message

    applied = MigrationExecutor(connection).recorder.applied_migrations()
    assert ("iam", "0006_v2_0_0") not in applied
    assert ("sta", "0009_v2_0_0") not in applied
    assert Role.objects.filter(pk=duplicate_role.pk).exists()

    duplicate_role.delete()
    siteless_thing.delete()
    apps = _migrate()
    assert apps.get_model("sta", "MonitoringSite").objects.filter(pk=seeded["thing"].pk).exists()
