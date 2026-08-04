import pytest

from core.iam.models import Role, User, Workspace
from core.sta.models import Thing
from tests.core.iam.factories import RoleFactory
from tests.e2e.scenarios import cleanup_scenario, create_scenario


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def scenario_dependencies(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    for name in ("Viewer", "Editor", "Data Loader"):
        RoleFactory(name=name, workspace=None)


def test_scenario_uses_generated_ids_and_cleans_up_all_workspace_data():
    scenario = create_scenario("scenario-one")

    assert scenario["users"]["owner"]["email"].endswith(
        "+scenario-one@example.com"
    )
    assert scenario["fixtures"]["workspaces"]["public"]["id"]
    assert scenario["fixtures"]["things"]["public"]["id"]
    assert User.objects.filter(email__contains="+scenario-one@").count() == 7
    assert Workspace.objects.count() == 3
    assert Thing.objects.count() == 5

    cleanup_scenario("scenario-one")

    assert not User.objects.filter(email__contains="+scenario-one@").exists()
    assert not Workspace.objects.exists()
    assert not Thing.objects.exists()


def test_scenarios_do_not_share_users_or_resource_ids():
    first = create_scenario("scenario-first")
    second = create_scenario("scenario-second")

    assert first["users"]["owner"]["email"] != second["users"]["owner"]["email"]
    assert (
        first["fixtures"]["workspaces"]["public"]["id"]
        != second["fixtures"]["workspaces"]["public"]["id"]
    )
    assert (
        first["fixtures"]["datastreams"]["public"]["id"]
        != second["fixtures"]["datastreams"]["public"]["id"]
    )

    cleanup_scenario("scenario-first")
    assert Role.objects.count() == 3
    assert User.objects.filter(email__contains="+scenario-second@").count() == 7

    cleanup_scenario("scenario-second")
