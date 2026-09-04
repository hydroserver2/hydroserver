import pytest
from django.core.exceptions import ValidationError

from core.iam.models import Collaborator
from tests.core.iam.factories import (
    CollaboratorFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)

pytestmark = pytest.mark.django_db


# --- clean(): owner cannot be a collaborator ------------------------------------


def test_clean_raises_when_user_is_workspace_owner():
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    role = RoleFactory(global_role=True)
    collaborator = CollaboratorFactory.build(workspace=workspace, user=owner, role=role)

    with pytest.raises(ValidationError):
        collaborator.clean()


def test_clean_allows_non_owner_user():
    workspace = WorkspaceFactory()
    role = RoleFactory(global_role=True)
    collaborator = CollaboratorFactory.build(workspace=workspace, role=role)

    collaborator.clean()  # does not raise


# --- clean(): role must belong to the workspace ---------------------------------


def test_clean_raises_when_role_belongs_to_a_different_workspace():
    workspace = WorkspaceFactory()
    other_workspace = WorkspaceFactory()
    role = RoleFactory(workspace=other_workspace)
    collaborator = CollaboratorFactory.build(workspace=workspace, role=role)

    with pytest.raises(ValidationError):
        collaborator.clean()


def test_clean_allows_global_role():
    workspace = WorkspaceFactory()
    role = RoleFactory(global_role=True)
    collaborator = CollaboratorFactory.build(workspace=workspace, role=role)

    collaborator.clean()  # does not raise


def test_clean_allows_role_belonging_to_the_same_workspace():
    workspace = WorkspaceFactory()
    role = RoleFactory(workspace=workspace)
    collaborator = CollaboratorFactory.build(workspace=workspace, role=role)

    collaborator.clean()  # does not raise


# --- full_clean(): duplicate collaborator constraint -----------------------------


def test_full_clean_raises_when_user_already_collaborates():
    workspace = WorkspaceFactory()
    role = RoleFactory(global_role=True)
    existing = CollaboratorFactory(workspace=workspace, role=role)
    duplicate = Collaborator(workspace=workspace, user=existing.user, role=role)

    with pytest.raises(ValidationError):
        duplicate.full_clean()
