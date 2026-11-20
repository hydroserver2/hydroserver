import pytest
from django.urls import reverse

from core.iam.models import User


pytestmark = pytest.mark.django_db


def test_role_load_defaults_preview_reads_yaml_fixture(client):
    client.force_login(
        User.objects.create_superuser(email="admin@example.test", password="password")
    )

    response = client.get(reverse("admin:iam_role_load_defaults"))

    assert response.status_code == 200
    roles = {str(obj) for obj, _ in response.context["to_create"]}
    assert roles
    assert all(children for _, children in response.context["to_create"])
