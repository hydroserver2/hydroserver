import pytest

from django.core.management import call_command

from core.iam.models import Role


@pytest.fixture
def default_editor_role(db):
    call_command("loaddata", "default_roles", verbosity=0)
    return Role.objects.get(name="Editor", workspace=None)
