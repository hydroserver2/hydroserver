import pytest
from django.urls import reverse

from core.iam.models import User, UserType


pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    admin = User.objects.create_superuser(email="admin@example.test", password="password")
    client.force_login(admin)
    return client


def test_profile_edit_offers_public_user_types(client):
    UserType.objects.create(name="Researcher", public=True)
    UserType.objects.create(name="Hidden", public=False)
    user = User.objects.create_user(
        email="profile@example.test", password="password", user_type="Researcher"
    )
    client.force_login(user)

    response = client.get(reverse("account_profile_edit"))

    choices = dict(response.context["form"].fields["user_type"].choices)
    assert "Researcher" in choices
    assert "Hidden" not in choices


def test_profile_edit_without_public_user_types_offers_other(client):
    user = User.objects.create_user(email="profile@example.test", password="password")
    client.force_login(user)

    page = client.get(reverse("account_profile_edit"))
    response = client.post(
        reverse("account_profile_edit"),
        {"first_name": "Jane", "last_name": "Doe", "user_type": "Other"},
    )

    assert page.context["form"].fields["user_type"].choices == [("Other", "Other")]
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.user_type == "Other"


def test_profile_edit_keeps_unlisted_user_type(client):
    UserType.objects.create(name="Researcher", public=True)
    user = User.objects.create_superuser(email="root@example.test", password="password")
    client.force_login(user)

    page = client.get(reverse("account_profile_edit"))
    response = client.post(
        reverse("account_profile_edit"),
        {"first_name": "Root", "last_name": "User", "user_type": "Admin"},
    )

    assert ("Admin", "Admin") in page.context["form"].fields["user_type"].choices
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.user_type == "Admin"


def test_superuser_defaults_to_admin_user_type():
    user = User.objects.create_superuser(email="root@example.test", password="password")

    assert user.user_type == "Admin"


def test_user_admin_sets_free_text_user_type(admin_client):
    user = User.objects.create_user(
        email="promoted@example.test", password="password", user_type="Other"
    )

    response = admin_client.post(
        reverse("admin:iam_user_change", args=[user.pk]),
        {
            "email": user.email,
            "first_name": "",
            "last_name": "",
            "user_type": "Data Steward",
            "is_active": "on",
            "owned_workspace_limit": "",
            "date_joined_0": "2026-01-01",
            "date_joined_1": "00:00:00",
        },
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.user_type == "Data Steward"


def test_user_type_admin_loads_defaults(admin_client):
    changelist = admin_client.get(reverse("admin:iam_usertype_changelist"))
    preview = admin_client.get(reverse("admin:iam_usertype_load_defaults"))
    response = admin_client.post(reverse("admin:iam_usertype_load_defaults"))

    assert reverse("admin:iam_usertype_load_defaults").encode() in changelist.content
    assert "University Faculty" in {str(obj) for obj, _ in preview.context["to_create"]}
    assert response.status_code == 302
    assert UserType.objects.filter(name="University Faculty", public=True).exists()
    assert UserType.objects.filter(name="Admin", public=False).exists()
