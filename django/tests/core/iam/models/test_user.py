import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

from tests.core.iam.factories import UserFactory

User = get_user_model()

pytestmark = pytest.mark.django_db


# --- UserManager.create_user ------------------------------------------------


def test_create_user_sets_password():
    user = User.objects.create_user(
        email="person@example.com",
        password="password123",
        first_name="A",
        last_name="B",
        user_type="Other",
    )

    assert user.check_password("password123")


def test_create_user_raises_without_email():
    with pytest.raises(ValueError):
        User.objects.create_user(
            email="",
            password="password123",
            first_name="A",
            last_name="B",
            user_type="Other",
        )


# --- UserManager.create_superuser --------------------------------------------


def test_create_superuser_sets_staff_and_superuser_flags():
    user = User.objects.create_superuser(
        email="admin@example.com", password="password123", first_name="A", last_name="B"
    )

    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.user_type == "Admin"


def test_create_superuser_creates_verified_primary_email_address():
    user = User.objects.create_superuser(
        email="admin2@example.com", password="password123", first_name="A", last_name="B"
    )

    email_address = EmailAddress.objects.get(user=user)
    assert email_address.email == user.email
    assert email_address.verified is True
    assert email_address.primary is True


# --- save() --------------------------------------------------------------------


def test_save_lowercases_email():
    user = UserFactory.build(email="Mixed.Case@Example.COM")

    user.save()

    assert user.email == "mixed.case@example.com"