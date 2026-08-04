import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.iam.models import Workspace
from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.tree_factories import build_workspaces

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


# --- delete() --------------------------------------------------------------------


def test_delete_removes_owned_workspaces_and_full_tree():
    user = UserFactory()
    workspaces = build_workspaces(
        user,
        workspace_count=2,
        things_per_workspace=2,
        datastreams_per_thing=1,
        observations_per_datastream=1_000,
    )
    other_user = UserFactory()
    other_workspace = WorkspaceFactory(owner=other_user)

    user.delete()

    assert not User.objects.filter(pk=user.pk).exists()
    assert not Workspace.objects.filter(pk__in=[w.pk for w in workspaces]).exists()
    assert Workspace.objects.filter(pk=other_workspace.pk).exists()


# --- QuerySet.delete() -------------------------------------------------------------


def test_queryset_delete_removes_users_and_full_tree_in_bulk():
    to_delete = UserFactory.create_batch(2)
    for user in to_delete:
        build_workspaces(
            user,
            workspace_count=1,
            things_per_workspace=1,
            datastreams_per_thing=1,
            observations_per_datastream=100,
        )
    kept_user = UserFactory()
    kept_workspace = WorkspaceFactory(owner=kept_user)

    User.objects.filter(pk__in=[u.pk for u in to_delete]).delete()

    assert not User.objects.filter(pk__in=[u.pk for u in to_delete]).exists()
    assert not Workspace.objects.filter(owner__in=to_delete).exists()
    assert Workspace.objects.filter(pk=kept_workspace.pk).exists()


USER_DELETE_SHAPES = [
    pytest.param(1, 2, 1, 1_000, id="1_user-2_workspaces-1_thing-1000_observations_each"),
    pytest.param(3, 2, 1, 1_000, id="3_users-2_workspaces-1_thing-1000_observations_each"),
    pytest.param(10, 1, 1, 100, id="10_users-1_workspace-1_thing-100_observations_each"),
]


@pytest.mark.parametrize(
    "user_count,workspaces_per_user,things_per_workspace,observations_per_datastream",
    USER_DELETE_SHAPES,
)
def test_queryset_delete_query_count_does_not_scale_with_user_count(
    user_count, workspaces_per_user, things_per_workspace, observations_per_datastream
):
    small = UserFactory.create_batch(user_count)
    for user in small:
        build_workspaces(user, workspaces_per_user, things_per_workspace, 1, observations_per_datastream)

    large = UserFactory.create_batch(user_count * 2)
    for user in large:
        build_workspaces(user, workspaces_per_user, things_per_workspace, 1, observations_per_datastream)

    with CaptureQueriesContext(connection) as small_queries:
        User.objects.filter(pk__in=[u.pk for u in small]).delete()

    with CaptureQueriesContext(connection) as large_queries:
        User.objects.filter(pk__in=[u.pk for u in large]).delete()

    assert len(small_queries) == len(large_queries)
