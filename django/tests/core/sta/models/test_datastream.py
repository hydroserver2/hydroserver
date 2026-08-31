import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.sta.models import Datastream, Observation
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory
from tests.core.tree_factories import bulk_create_observations

pytestmark = pytest.mark.django_db


# --- tags validation ---------------------------------------------------------------


def test_full_clean_rejects_non_dict_tags():
    datastream = DatastreamFactory()
    datastream.tags = ["season", "summer"]

    with pytest.raises(ValidationError):
        datastream.full_clean()


def test_full_clean_rejects_non_string_tag_values():
    datastream = DatastreamFactory()
    datastream.tags = {"count": 1}

    with pytest.raises(ValidationError):
        datastream.full_clean()


def test_full_clean_rejects_empty_tag_key():
    datastream = DatastreamFactory()
    datastream.tags = {"": "summer"}

    with pytest.raises(ValidationError):
        datastream.full_clean()


def test_full_clean_rejects_empty_tag_value():
    datastream = DatastreamFactory()
    datastream.tags = {"season": ""}

    with pytest.raises(ValidationError):
        datastream.full_clean()


# --- delete() --------------------------------------------------------------------


def test_delete_removes_datastream_and_its_observations_only():
    monitoring_site = MonitoringSiteFactory()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    bulk_create_observations(datastream, 1_000)
    sibling = DatastreamFactory(monitoring_site=monitoring_site)
    bulk_create_observations(sibling, 10)

    datastream.delete()

    assert not Datastream.objects.filter(pk=datastream.pk).exists()
    assert not Observation.objects.filter(datastream_id=datastream.pk).exists()
    assert Datastream.objects.filter(pk=sibling.pk).exists()
    assert Observation.objects.filter(datastream_id=sibling.pk).count() == 10


# --- QuerySet.delete() -------------------------------------------------------------


def test_queryset_delete_removes_datastreams_and_observations_in_bulk():
    monitoring_site = MonitoringSiteFactory()
    to_delete = DatastreamFactory.create_batch(3, monitoring_site=monitoring_site)
    for datastream in to_delete:
        bulk_create_observations(datastream, 100)
    kept = DatastreamFactory(monitoring_site=monitoring_site)
    bulk_create_observations(kept, 10)

    Datastream.objects.filter(pk__in=[d.pk for d in to_delete]).delete()

    assert not Datastream.objects.filter(pk__in=[d.pk for d in to_delete]).exists()
    assert not Observation.objects.filter(datastream__in=to_delete).exists()
    assert Datastream.objects.filter(pk=kept.pk).exists()
    assert Observation.objects.filter(datastream_id=kept.pk).count() == 10


DATASTREAM_DELETE_SHAPES = [
    pytest.param(1, 1_000, id="1_datastream-1000_observations_each"),
    pytest.param(5, 1_000, id="5_datastreams-1000_observations_each"),
    pytest.param(20, 100, id="20_datastreams-100_observations_each"),
]


@pytest.mark.parametrize(
    "datastream_count,observations_per_datastream", DATASTREAM_DELETE_SHAPES
)
def test_queryset_delete_query_count_does_not_scale_with_datastream_count(
    datastream_count, observations_per_datastream
):
    monitoring_site = MonitoringSiteFactory()

    small = DatastreamFactory.create_batch(datastream_count, monitoring_site=monitoring_site)
    for datastream in small:
        bulk_create_observations(datastream, observations_per_datastream)

    large = DatastreamFactory.create_batch(datastream_count * 2, monitoring_site=monitoring_site)
    for datastream in large:
        bulk_create_observations(datastream, observations_per_datastream)

    with CaptureQueriesContext(connection) as small_queries:
        Datastream.objects.filter(pk__in=[d.pk for d in small]).delete()

    with CaptureQueriesContext(connection) as large_queries:
        Datastream.objects.filter(pk__in=[d.pk for d in large]).delete()

    assert len(small_queries) == len(large_queries)
