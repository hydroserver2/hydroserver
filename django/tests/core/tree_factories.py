from core.sta.models import Observation
from tests.core.iam.factories import WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, ObservationFactory, ThingFactory


def bulk_create_observations(datastream, count):
    observations = ObservationFactory.build_batch(count, datastream=datastream)
    return Observation.objects.bulk_create(observations)


def build_datastreams(thing, datastream_count, observations_per_datastream):
    datastreams = DatastreamFactory.create_batch(datastream_count, thing=thing)
    for datastream in datastreams:
        bulk_create_observations(datastream, observations_per_datastream)
    return datastreams


def build_things(workspace, thing_count, datastreams_per_thing, observations_per_datastream):
    things = ThingFactory.create_batch(thing_count, workspace=workspace)
    for thing in things:
        build_datastreams(thing, datastreams_per_thing, observations_per_datastream)
    return things


def build_workspaces(
    owner, workspace_count, things_per_workspace, datastreams_per_thing, observations_per_datastream
):
    workspaces = [
        WorkspaceFactory(owner=owner, name=f"{owner.username} Workspace {i}")
        for i in range(workspace_count)
    ]
    for workspace in workspaces:
        build_things(workspace, things_per_workspace, datastreams_per_thing, observations_per_datastream)
    return workspaces
