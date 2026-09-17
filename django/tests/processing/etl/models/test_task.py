import pytest
from django.core.exceptions import ValidationError

from processing.etl.models import EtlMapping
from tests.core.iam.factories import WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory
from tests.processing.etl.factories import DataConnectionFactory, EtlMappingFactory, EtlTaskFactory

pytestmark = pytest.mark.django_db


# --- EtlMapping.clean(): target datastream must share the task's workspace -----------------


def test_full_clean_rejects_target_datastream_from_another_workspace():
    workspace = WorkspaceFactory()
    other_workspace = WorkspaceFactory()
    etl_task = EtlTaskFactory(data_connection=DataConnectionFactory(workspace=workspace))
    datastream = DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=other_workspace))
    mapping = EtlMapping(etl_task=etl_task, source_identifier="col", target_datastream=datastream)

    with pytest.raises(ValidationError):
        mapping.full_clean()


def test_full_clean_allows_target_datastream_in_same_workspace():
    workspace = WorkspaceFactory()
    etl_task = EtlTaskFactory(data_connection=DataConnectionFactory(workspace=workspace))
    datastream = DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=workspace))
    mapping = EtlMapping(etl_task=etl_task, source_identifier="col", target_datastream=datastream)

    mapping.full_clean()  # does not raise


# --- EtlMapping: unique_etl_mapping_target_datastream constraint ---------------------------


def test_full_clean_rejects_target_datastream_already_mapped_by_another_task():
    workspace = WorkspaceFactory()
    etl_task_1 = EtlTaskFactory(data_connection=DataConnectionFactory(workspace=workspace))
    etl_task_2 = EtlTaskFactory(data_connection=DataConnectionFactory(workspace=workspace))
    datastream = DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=workspace))
    EtlMappingFactory(etl_task=etl_task_1, target_datastream=datastream)

    mapping = EtlMapping(etl_task=etl_task_2, source_identifier="col2", target_datastream=datastream)

    with pytest.raises(ValidationError):
        mapping.full_clean()
