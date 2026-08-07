import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.sta.models import Datastream, Observation, MonitoringSite
from tests.core.iam.factories import WorkspaceFactory
from tests.core.sta.factories import MonitoringSiteFactory
from tests.core.tree_factories import build_datastreams

pytestmark = pytest.mark.django_db


# --- delete() --------------------------------------------------------------------


def test_delete_removes_monitoring_site_datastreams_and_observations_only():
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    build_datastreams(monitoring_site, datastream_count=3, observations_per_datastream=1_000)
    sibling = MonitoringSiteFactory(workspace=workspace)
    build_datastreams(sibling, datastream_count=1, observations_per_datastream=10)

    monitoring_site.delete()

    assert not MonitoringSite.objects.filter(pk=monitoring_site.pk).exists()
    assert not Datastream.objects.filter(monitoring_site_id=monitoring_site.pk).exists()
    assert not Observation.objects.filter(datastream__monitoring_site_id=monitoring_site.pk).exists()
    assert MonitoringSite.objects.filter(pk=sibling.pk).exists()
    assert Datastream.objects.filter(monitoring_site_id=sibling.pk).count() == 1


# --- QuerySet.delete() -------------------------------------------------------------


def test_queryset_delete_removes_monitoring_sites_datastreams_and_observations_in_bulk():
    workspace = WorkspaceFactory()
    to_delete = MonitoringSiteFactory.create_batch(3, workspace=workspace)
    for monitoring_site in to_delete:
        build_datastreams(monitoring_site, datastream_count=2, observations_per_datastream=100)
    kept = MonitoringSiteFactory(workspace=workspace)
    build_datastreams(kept, datastream_count=1, observations_per_datastream=10)

    MonitoringSite.objects.filter(pk__in=[t.pk for t in to_delete]).delete()

    assert not MonitoringSite.objects.filter(pk__in=[t.pk for t in to_delete]).exists()
    assert not Datastream.objects.filter(monitoring_site__in=to_delete).exists()
    assert not Observation.objects.filter(datastream__monitoring_site__in=to_delete).exists()
    assert MonitoringSite.objects.filter(pk=kept.pk).exists()


MONITORING_SITE_DELETE_SHAPES = [
    pytest.param(1, 3, 1_000, id="1_monitoring_site-3_datastreams-1000_observations_each"),
    pytest.param(5, 3, 1_000, id="5_monitoring_sites-3_datastreams-1000_observations_each"),
    pytest.param(20, 1, 100, id="20_monitoring_sites-1_datastream-100_observations_each"),
]


@pytest.mark.parametrize(
    "monitoring_site_count,datastreams_per_monitoring_site,observations_per_datastream", MONITORING_SITE_DELETE_SHAPES
)
def test_queryset_delete_query_count_does_not_scale_with_monitoring_site_count(
    monitoring_site_count, datastreams_per_monitoring_site, observations_per_datastream
):
    workspace = WorkspaceFactory()

    small = MonitoringSiteFactory.create_batch(monitoring_site_count, workspace=workspace)
    for monitoring_site in small:
        build_datastreams(monitoring_site, datastreams_per_monitoring_site, observations_per_datastream)

    large = MonitoringSiteFactory.create_batch(monitoring_site_count * 2, workspace=workspace)
    for monitoring_site in large:
        build_datastreams(monitoring_site, datastreams_per_monitoring_site, observations_per_datastream)

    with CaptureQueriesContext(connection) as small_queries:
        MonitoringSite.objects.filter(pk__in=[t.pk for t in small]).delete()

    with CaptureQueriesContext(connection) as large_queries:
        MonitoringSite.objects.filter(pk__in=[t.pk for t in large]).delete()

    assert len(small_queries) == len(large_queries)
