import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.iam.models import Workspace
from core.sta.models import (
    Datastream,
    Observation,
    ObservedProperty,
    ProcessingLevel,
    Method,
    MonitoringSite,
    Unit,
)
from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.tree_factories import build_monitoring_sites

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

    with pytest.raises(ValidationError):
        workspace.initiate_transfer(UserFactory())


def test_initiate_transfer_raises_when_new_owner_is_current_owner():
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)

    with pytest.raises(ValidationError):
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


def test_accept_transfer_raises_when_none_pending():
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


def test_reject_transfer_raises_when_none_pending():
    workspace = WorkspaceFactory()

    with pytest.raises(ValueError):
        workspace.reject_transfer()


# --- delete() --------------------------------------------------------------------


def test_delete_removes_workspace_tree_including_same_workspace_vocab_items():
    workspace = WorkspaceFactory()
    build_monitoring_sites(workspace, monitoring_site_count=3, datastreams_per_monitoring_site=2, observations_per_datastream=1_000)
    sibling = WorkspaceFactory()
    build_monitoring_sites(sibling, monitoring_site_count=1, datastreams_per_monitoring_site=1, observations_per_datastream=10)

    workspace.delete()

    assert not Workspace.objects.filter(pk=workspace.pk).exists()
    assert not MonitoringSite.objects.filter(workspace_id=workspace.pk).exists()
    assert not Datastream.objects.filter(monitoring_site__workspace_id=workspace.pk).exists()
    assert not Observation.objects.filter(datastream__monitoring_site__workspace_id=workspace.pk).exists()
    # These are CASCADE from Workspace but PROTECT from Datastream -- proving the
    # ordering issue (deleting a Workspace whose own Datastreams still reference
    # its own Method/ObservedProperty/ProcessingLevel/Unit) no longer raises.
    assert not Method.objects.filter(workspace_id=workspace.pk).exists()
    assert not ObservedProperty.objects.filter(workspace_id=workspace.pk).exists()
    assert not ProcessingLevel.objects.filter(workspace_id=workspace.pk).exists()
    assert not Unit.objects.filter(workspace_id=workspace.pk).exists()
    assert Workspace.objects.filter(pk=sibling.pk).exists()
    assert MonitoringSite.objects.filter(workspace=sibling).count() == 1


# --- QuerySet.delete() -------------------------------------------------------------


def test_queryset_delete_removes_workspaces_and_full_tree_in_bulk():
    to_delete = []
    for _ in range(2):
        ws = WorkspaceFactory()
        build_monitoring_sites(ws, monitoring_site_count=2, datastreams_per_monitoring_site=1, observations_per_datastream=100)
        to_delete.append(ws)
    kept = WorkspaceFactory()
    build_monitoring_sites(kept, monitoring_site_count=1, datastreams_per_monitoring_site=1, observations_per_datastream=10)

    Workspace.objects.filter(pk__in=[w.pk for w in to_delete]).delete()

    assert not Workspace.objects.filter(pk__in=[w.pk for w in to_delete]).exists()
    assert not MonitoringSite.objects.filter(workspace__in=to_delete).exists()
    assert not Datastream.objects.filter(monitoring_site__workspace__in=to_delete).exists()
    assert Workspace.objects.filter(pk=kept.pk).exists()


WORKSPACE_DELETE_SHAPES = [
    pytest.param(1, 3, 2, 1_000, id="1_workspace-3_monitoring_sites-2_datastreams-1000_observations_each"),
    pytest.param(3, 3, 2, 1_000, id="3_workspaces-3_monitoring_sites-2_datastreams-1000_observations_each"),
    pytest.param(10, 1, 1, 100, id="10_workspaces-1_monitoring_site-1_datastream-100_observations_each"),
]


@pytest.mark.parametrize(
    "workspace_count,monitoring_sites_per_workspace,datastreams_per_monitoring_site,observations_per_datastream",
    WORKSPACE_DELETE_SHAPES,
)
def test_queryset_delete_query_count_does_not_scale_with_workspace_count(
    workspace_count, monitoring_sites_per_workspace, datastreams_per_monitoring_site, observations_per_datastream
):
    small = WorkspaceFactory.create_batch(workspace_count)
    for workspace in small:
        build_monitoring_sites(workspace, monitoring_sites_per_workspace, datastreams_per_monitoring_site, observations_per_datastream)

    large = WorkspaceFactory.create_batch(workspace_count * 2)
    for workspace in large:
        build_monitoring_sites(workspace, monitoring_sites_per_workspace, datastreams_per_monitoring_site, observations_per_datastream)

    with CaptureQueriesContext(connection) as small_queries:
        Workspace.objects.filter(pk__in=[w.pk for w in small]).delete()

    with CaptureQueriesContext(connection) as large_queries:
        Workspace.objects.filter(pk__in=[w.pk for w in large]).delete()

    assert len(small_queries) == len(large_queries)
