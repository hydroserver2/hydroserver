import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.sta.models import Datastream, DatastreamLinkedResource, Observation
from tests.core.iam.factories import WorkspaceFactory
from tests.core.sta.factories import (
    DatastreamFactory,
    MethodFactory,
    MonitoringSiteFactory,
    ObservedPropertyFactory,
    ProcessingLevelFactory,
    UnitFactory,
)
from tests.core.tree_factories import bulk_create_observations

pytestmark = pytest.mark.django_db


# --- clean(): linked resource mode cannot be switched (shared mixin) -------------


def test_full_clean_rejects_datastream_linked_resource_mode_switch():
    linked_resource = DatastreamLinkedResource.objects.create(
        datastream=DatastreamFactory(),
        name="Datastream Report",
        type="Report",
        url="https://example.com/report.pdf",
    )
    linked_resource.url = ""
    linked_resource.file = SimpleUploadedFile("photo.png", b"photo")

    with pytest.raises(ValidationError):
        linked_resource.full_clean()


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


# --- clean(): related items must share the monitoring_site's workspace -----------


def test_full_clean_rejects_observed_property_from_another_workspace():
    workspace = WorkspaceFactory()
    other_workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    datastream = DatastreamFactory.build(
        monitoring_site=monitoring_site,
        observed_property=ObservedPropertyFactory(workspace=other_workspace),
        processing_level=ProcessingLevelFactory(workspace=workspace),
        method=MethodFactory(workspace=workspace),
        unit=UnitFactory(workspace=workspace),
    )

    with pytest.raises(ValidationError):
        datastream.full_clean()


def test_full_clean_rejects_processing_level_from_another_workspace():
    workspace = WorkspaceFactory()
    other_workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    datastream = DatastreamFactory.build(
        monitoring_site=monitoring_site,
        observed_property=ObservedPropertyFactory(workspace=workspace),
        processing_level=ProcessingLevelFactory(workspace=other_workspace),
        method=MethodFactory(workspace=workspace),
        unit=UnitFactory(workspace=workspace),
    )

    with pytest.raises(ValidationError):
        datastream.full_clean()


def test_full_clean_rejects_method_from_another_workspace():
    workspace = WorkspaceFactory()
    other_workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    datastream = DatastreamFactory.build(
        monitoring_site=monitoring_site,
        observed_property=ObservedPropertyFactory(workspace=workspace),
        processing_level=ProcessingLevelFactory(workspace=workspace),
        method=MethodFactory(workspace=other_workspace),
        unit=UnitFactory(workspace=workspace),
    )

    with pytest.raises(ValidationError):
        datastream.full_clean()


def test_full_clean_rejects_unit_from_another_workspace():
    workspace = WorkspaceFactory()
    other_workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    datastream = DatastreamFactory.build(
        monitoring_site=monitoring_site,
        observed_property=ObservedPropertyFactory(workspace=workspace),
        processing_level=ProcessingLevelFactory(workspace=workspace),
        method=MethodFactory(workspace=workspace),
        unit=UnitFactory(workspace=other_workspace),
    )

    with pytest.raises(ValidationError):
        datastream.full_clean()


def test_full_clean_allows_global_observed_property():
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    datastream = DatastreamFactory.build(
        monitoring_site=monitoring_site,
        observed_property=ObservedPropertyFactory(workspace=None),
        processing_level=ProcessingLevelFactory(workspace=workspace),
        method=MethodFactory(workspace=workspace),
        unit=UnitFactory(workspace=workspace),
    )

    datastream.full_clean()  # does not raise


def test_full_clean_allows_same_workspace_related_items():
    datastream = DatastreamFactory()

    datastream.full_clean()  # does not raise


# --- clean(): monitoring_site cannot move to another workspace -------------------


def test_full_clean_rejects_monitoring_site_from_another_workspace():
    workspace = WorkspaceFactory()
    other_workspace = WorkspaceFactory()
    datastream = DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=workspace))
    datastream.monitoring_site = MonitoringSiteFactory(workspace=other_workspace)

    with pytest.raises(ValidationError):
        datastream.full_clean()


def test_full_clean_allows_monitoring_site_in_same_workspace():
    workspace = WorkspaceFactory()
    datastream = DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=workspace))
    datastream.monitoring_site = MonitoringSiteFactory(workspace=workspace)

    datastream.full_clean()  # does not raise


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
