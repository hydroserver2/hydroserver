import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.sta.models import Datastream, Observation, Thing
from tests.core.iam.factories import WorkspaceFactory
from tests.core.sta.factories import ThingFactory
from tests.core.tree_factories import build_datastreams

pytestmark = pytest.mark.django_db


# --- delete() --------------------------------------------------------------------


def test_delete_removes_thing_datastreams_and_observations_only():
    workspace = WorkspaceFactory()
    thing = ThingFactory(workspace=workspace)
    build_datastreams(thing, datastream_count=3, observations_per_datastream=1_000)
    sibling = ThingFactory(workspace=workspace)
    build_datastreams(sibling, datastream_count=1, observations_per_datastream=10)

    thing.delete()

    assert not Thing.objects.filter(pk=thing.pk).exists()
    assert not Datastream.objects.filter(thing_id=thing.pk).exists()
    assert not Observation.objects.filter(datastream__thing_id=thing.pk).exists()
    assert Thing.objects.filter(pk=sibling.pk).exists()
    assert Datastream.objects.filter(thing_id=sibling.pk).count() == 1


# --- QuerySet.delete() -------------------------------------------------------------


def test_queryset_delete_removes_things_datastreams_and_observations_in_bulk():
    workspace = WorkspaceFactory()
    to_delete = ThingFactory.create_batch(3, workspace=workspace)
    for thing in to_delete:
        build_datastreams(thing, datastream_count=2, observations_per_datastream=100)
    kept = ThingFactory(workspace=workspace)
    build_datastreams(kept, datastream_count=1, observations_per_datastream=10)

    Thing.objects.filter(pk__in=[t.pk for t in to_delete]).delete()

    assert not Thing.objects.filter(pk__in=[t.pk for t in to_delete]).exists()
    assert not Datastream.objects.filter(thing__in=to_delete).exists()
    assert not Observation.objects.filter(datastream__thing__in=to_delete).exists()
    assert Thing.objects.filter(pk=kept.pk).exists()


THING_DELETE_SHAPES = [
    pytest.param(1, 3, 1_000, id="1_thing-3_datastreams-1000_observations_each"),
    pytest.param(5, 3, 1_000, id="5_things-3_datastreams-1000_observations_each"),
    pytest.param(20, 1, 100, id="20_things-1_datastream-100_observations_each"),
]


@pytest.mark.parametrize(
    "thing_count,datastreams_per_thing,observations_per_datastream", THING_DELETE_SHAPES
)
def test_queryset_delete_query_count_does_not_scale_with_thing_count(
    thing_count, datastreams_per_thing, observations_per_datastream
):
    workspace = WorkspaceFactory()

    small = ThingFactory.create_batch(thing_count, workspace=workspace)
    for thing in small:
        build_datastreams(thing, datastreams_per_thing, observations_per_datastream)

    large = ThingFactory.create_batch(thing_count * 2, workspace=workspace)
    for thing in large:
        build_datastreams(thing, datastreams_per_thing, observations_per_datastream)

    with CaptureQueriesContext(connection) as small_queries:
        Thing.objects.filter(pk__in=[t.pk for t in small]).delete()

    with CaptureQueriesContext(connection) as large_queries:
        Thing.objects.filter(pk__in=[t.pk for t in large]).delete()

    assert len(small_queries) == len(large_queries)
