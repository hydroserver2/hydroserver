from core.sta.models import Observation
from tests.core.iam.factories import WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, ObservationFactory, MonitoringSiteFactory


def bulk_create_observations(datastream, count):
    observations = ObservationFactory.build_batch(count, datastream=datastream)
    return Observation.objects.bulk_create(observations)


def build_datastreams(monitoring_site, datastream_count, observations_per_datastream):
    datastreams = DatastreamFactory.create_batch(datastream_count, monitoring_site=monitoring_site)
    for datastream in datastreams:
        bulk_create_observations(datastream, observations_per_datastream)
    return datastreams


def build_monitoring_sites(workspace, monitoring_site_count, datastreams_per_monitoring_site, observations_per_datastream):
    monitoring_sites = MonitoringSiteFactory.create_batch(monitoring_site_count, workspace=workspace)
    for monitoring_site in monitoring_sites:
        build_datastreams(monitoring_site, datastreams_per_monitoring_site, observations_per_datastream)
    return monitoring_sites


def build_workspaces(
    owner, workspace_count, monitoring_sites_per_workspace, datastreams_per_monitoring_site, observations_per_datastream
):
    workspaces = [
        WorkspaceFactory(owner=owner, name=f"{owner.username} Workspace {i}")
        for i in range(workspace_count)
    ]
    for workspace in workspaces:
        build_monitoring_sites(workspace, monitoring_sites_per_workspace, datastreams_per_monitoring_site, observations_per_datastream)
    return workspaces
