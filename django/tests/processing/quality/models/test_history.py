import pytest
from django.core.exceptions import ValidationError

from processing.quality.models import QCHistory
from tests.core.iam.factories import WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory, ProcessingLevelFactory
from tests.processing.quality.factories import QCHistoryFactory

pytestmark = pytest.mark.django_db


def test_full_clean_rejects_datastreams_from_different_workspaces():
    managed = DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=WorkspaceFactory()))
    source = DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=WorkspaceFactory()))
    history = QCHistory(managed_datastream=managed, source_datastream=source)

    with pytest.raises(ValidationError):
        history.full_clean()


def test_full_clean_rejects_matching_processing_levels():
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    processing_level = ProcessingLevelFactory(workspace=workspace)
    managed = DatastreamFactory(monitoring_site=monitoring_site, processing_level=processing_level)
    source = DatastreamFactory(monitoring_site=monitoring_site, processing_level=processing_level)
    history = QCHistory(managed_datastream=managed, source_datastream=source)

    with pytest.raises(ValidationError):
        history.full_clean()


def test_full_clean_allows_different_processing_levels_same_workspace():
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    managed = DatastreamFactory(
        monitoring_site=monitoring_site, processing_level=ProcessingLevelFactory(workspace=workspace)
    )
    source = DatastreamFactory(
        monitoring_site=monitoring_site, processing_level=ProcessingLevelFactory(workspace=workspace)
    )
    history = QCHistory(managed_datastream=managed, source_datastream=source)

    history.full_clean()  # does not raise


def test_full_clean_rejects_second_history_for_same_managed_datastream():
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    existing = QCHistoryFactory(
        managed_datastream=DatastreamFactory(monitoring_site=monitoring_site),
        source_datastream=DatastreamFactory(monitoring_site=monitoring_site),
    )
    other_source = DatastreamFactory(monitoring_site=monitoring_site)
    duplicate = QCHistory(managed_datastream=existing.managed_datastream, source_datastream=other_source)

    with pytest.raises(ValidationError):
        duplicate.full_clean()
