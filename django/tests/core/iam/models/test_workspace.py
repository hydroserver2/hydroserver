import pytest
from django.core.exceptions import ValidationError

from tests.core.iam.factories import UserFactory, WorkspaceFactory

pytestmark = pytest.mark.django_db


# --- clean(): owned_workspace_limit -------------------------------------------


def test_clean_raises_when_owner_at_workspace_limit():
    owner = UserFactory(owned_workspace_limit=1)
    WorkspaceFactory(owner=owner)
    second = WorkspaceFactory.build(owner=owner)

    with pytest.raises(ValidationError):
        second.clean()


def test_clean_allows_when_owner_under_limit():
    owner = UserFactory(owned_workspace_limit=2)
    WorkspaceFactory(owner=owner)
    second = WorkspaceFactory.build(owner=owner)

    second.clean()  # does not raise


def test_clean_allows_unlimited_when_limit_is_none():
    owner = UserFactory(owned_workspace_limit=None)
    WorkspaceFactory(owner=owner)
    WorkspaceFactory(owner=owner)
    third = WorkspaceFactory.build(owner=owner)

    third.clean()  # does not raise


def test_clean_skips_limit_check_when_updating_without_changing_owner():
    owner = UserFactory(owned_workspace_limit=0)
    workspace = WorkspaceFactory(owner=owner)
    workspace.name = "Renamed"

    workspace.clean()  # does not raise, even though owner is past the limit


def test_clean_checks_limit_when_owner_changes_on_update():
    workspace = WorkspaceFactory()

    new_owner = UserFactory(owned_workspace_limit=1)
    WorkspaceFactory(owner=new_owner)
    workspace.owner = new_owner

    with pytest.raises(ValidationError):
        workspace.clean()


# --- initiate_transfer ---------------------------------------------------------


def test_initiate_transfer_creates_confirmation():
    workspace = WorkspaceFactory()
    new_owner = UserFactory()

    workspace.initiate_transfer(new_owner)

    assert workspace.transfer_confirmation.new_owner == new_owner


def test_initiate_transfer_raises_when_already_pending():
    workspace = WorkspaceFactory()
    workspace.initiate_transfer(UserFactory())

    with pytest.raises(ValueError):
        workspace.initiate_transfer(UserFactory())


def test_initiate_transfer_raises_when_new_owner_is_current_owner():
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)

    with pytest.raises(ValueError):
        workspace.initiate_transfer(owner)


# --- accept_transfer ------------------------------------------------------------


def test_accept_transfer_changes_owner_and_clears_confirmation():
    workspace = WorkspaceFactory()
    new_owner = UserFactory()
    workspace.initiate_transfer(new_owner)

    workspace.accept_transfer()
    workspace.refresh_from_db()

    assert workspace.owner == new_owner
    assert workspace.transfer is None


def test_accept_transfer_raises_when_nothing_pending():
    workspace = WorkspaceFactory()

    with pytest.raises(ValueError):
        workspace.accept_transfer()


# --- reject_transfer ------------------------------------------------------------


def test_reject_transfer_clears_confirmation_without_changing_owner():
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    workspace.initiate_transfer(UserFactory())

    workspace.reject_transfer()
    workspace.refresh_from_db()

    assert workspace.owner == owner
    assert workspace.transfer is None


def test_reject_transfer_raises_when_nothing_pending():
    workspace = WorkspaceFactory()

    with pytest.raises(ValueError):
        workspace.reject_transfer()