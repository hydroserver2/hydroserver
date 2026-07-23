import pytest
from django.conf import settings
from django.contrib.auth.hashers import check_password

from core.iam.models import ServiceAccount
from tests.core.iam.factories import ServiceAccountFactory

pytestmark = pytest.mark.django_db


# --- save() ---------------------------------------------------------------------


def test_save_generates_key_on_creation():
    service_account = ServiceAccountFactory()

    assert service_account.key_hash != ""
    assert service_account.key_prefix != ""


def test_save_does_not_regenerate_key_if_already_set():
    service_account = ServiceAccountFactory.build(workspace=None)
    service_account.generate_key()
    existing_hash = service_account.key_hash

    service_account.save()

    assert service_account.key_hash == existing_hash


def test_save_populates_email_from_key_prefix_when_blank():
    service_account = ServiceAccountFactory()

    expected = f"{service_account.key_prefix}@service-accounts.{settings.SERVICE_ACCOUNT_EMAIL_DOMAIN}"
    
    assert service_account.email == expected


# --- generate_key() ---------------------------------------------------------------


def test_generate_key_returns_the_raw_key_which_is_not_persisted_as_is():
    service_account = ServiceAccountFactory()

    raw_key = service_account.generate_key()

    assert raw_key != service_account.key_hash
    assert check_password(raw_key, service_account.key_hash)


def test_generate_key_on_unsaved_instance_does_not_save():
    service_account = ServiceAccountFactory.build(workspace=None)

    service_account.generate_key()

    assert service_account._state.adding is True


def test_generate_key_on_saved_instance_persists_the_new_key():
    service_account = ServiceAccountFactory()
    old_prefix = service_account.key_prefix

    raw_key = service_account.generate_key()
    from_db = ServiceAccount.objects.get(pk=service_account.pk)

    assert from_db.key_prefix != old_prefix
    assert check_password(raw_key, from_db.key_hash)


# --- deactivate() ---------------------------------------------------------------


def test_deactivate_clears_key_and_marks_inactive():
    service_account = ServiceAccountFactory()

    service_account.deactivate()

    assert service_account.is_active is False
    assert service_account.key_hash == ""
    assert service_account.deactivated_at is not None