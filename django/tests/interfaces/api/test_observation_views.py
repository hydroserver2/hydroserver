from datetime import timedelta

import pytest
from django.utils import timezone

from core.sta.models import Observation
from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, ObservationFactory, ThingFactory

pytestmark = pytest.mark.django_db


def _observations_url(datastream_id):
    return f"/api/data/datastreams/{datastream_id}/observations"


def _detail_url(datastream_id, observation_id):
    return f"{_observations_url(datastream_id)}/{observation_id}"


def _make_datastream(workspace, **kwargs):
    return DatastreamFactory(thing=ThingFactory(workspace=workspace), **kwargs)


def _collaborator_blocking_edit(workspace):
    """A collaborator who can view but not edit the datastream, blocking every
    write action on its observations (they all gate on Datastream edit access
    before checking Observation-specific permissions)."""

    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Datastream", can_view=True)
    return CollaboratorFactory(workspace=workspace, role=role)


def _iso(dt):
    return dt.isoformat()


# --- get_observations ----------------------------------------------------------------


def test_get_observations_includes_public_observation_for_anonymous(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    observation = ObservationFactory(datastream=datastream)

    response = client.get(_observations_url(datastream.id))

    assert response.status_code == 200
    assert str(observation.id) in [o["id"] for o in response.json()]


def test_get_observations_returns_404_for_private_datastream_when_outsider(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace, private=True)
    ObservationFactory(datastream=datastream)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_observations_url(datastream.id))

    assert response.status_code == 404


def test_get_observations_includes_observation_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace, private=True)
    observation = ObservationFactory(datastream=datastream)
    client.force_login(owner)

    response = client.get(_observations_url(datastream.id))

    assert response.status_code == 200
    assert str(observation.id) in [o["id"] for o in response.json()]


def test_get_observations_row_format_returns_field_rows(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    ObservationFactory(datastream=datastream, result=99.5)

    response = client.get(f"{_observations_url(datastream.id)}?format=row")

    assert response.status_code == 200
    body = response.json()
    assert "phenomenonTime" in body["fields"]
    assert any(row[1] == 99.5 for row in body["data"])


def test_get_observations_column_format_returns_columnar_data(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    ObservationFactory(datastream=datastream, result=99.5)

    response = client.get(f"{_observations_url(datastream.id)}?format=column")

    assert response.status_code == 200
    assert 99.5 in response.json()["result"]


# --- create_observation ----------------------------------------------------------------


def test_create_observation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.post(
        _observations_url(datastream.id),
        data={"phenomenonTime": _iso(timezone.now()), "result": 12.3},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["result"] == 12.3


def test_create_observation_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)

    response = client.post(
        _observations_url(datastream.id),
        data={"phenomenonTime": _iso(timezone.now()), "result": 12.3},
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_observation_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    collaborator = _collaborator_blocking_edit(workspace)
    client.force_login(collaborator.user)

    response = client.post(
        _observations_url(datastream.id),
        data={"phenomenonTime": _iso(timezone.now()), "result": 12.3},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_observation_returns_409_for_duplicate_phenomenon_time(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    phenomenon_time = timezone.now()
    ObservationFactory(datastream=datastream, phenomenon_time=phenomenon_time)
    client.force_login(owner)

    response = client.post(
        _observations_url(datastream.id),
        data={"phenomenonTime": _iso(phenomenon_time), "result": 12.3},
        content_type="application/json",
    )

    assert response.status_code == 409


def test_create_observation_returns_400_for_invalid_result_qualifier_code(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.post(
        _observations_url(datastream.id),
        data={
            "phenomenonTime": _iso(timezone.now()),
            "result": 12.3,
            "resultQualifierCodes": ["BOGUS"],
        },
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_observation -------------------------------------------------------------------


def test_get_observation_returns_public_observation_for_anonymous(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    observation = ObservationFactory(datastream=datastream)

    response = client.get(_detail_url(datastream.id, observation.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(observation.id)


def test_get_observation_returns_404_for_private_datastream_observation_when_outsider(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace, private=True)
    observation = ObservationFactory(datastream=datastream)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(datastream.id, observation.id))

    assert response.status_code == 404


def test_get_observation_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace, private=True)
    observation = ObservationFactory(datastream=datastream)
    client.force_login(owner)

    response = client.get(_detail_url(datastream.id, observation.id))

    assert response.status_code == 200


def test_get_observation_returns_404_for_nonexistent_observation(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)

    response = client.get(
        _detail_url(datastream.id, "00000000-0000-0000-0000-000000000000")
    )

    assert response.status_code == 404


# --- delete_observation ----------------------------------------------------------------


def test_delete_observation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    observation = ObservationFactory(datastream=datastream)
    client.force_login(owner)

    response = client.delete(_detail_url(datastream.id, observation.id))

    assert response.status_code == 204
    assert client.get(_detail_url(datastream.id, observation.id)).status_code == 404


def test_delete_observation_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    observation = ObservationFactory(datastream=datastream)
    collaborator = _collaborator_blocking_edit(workspace)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(datastream.id, observation.id))

    assert response.status_code == 403


# --- insert_observations (bulk-create) --------------------------------------------------


def test_insert_observations_insert_mode_succeeds(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    now = timezone.now()
    client.force_login(owner)

    response = client.post(
        f"{_observations_url(datastream.id)}/bulk-create?mode=insert",
        data={
            "fields": ["phenomenonTime", "result"],
            "data": [
                [_iso(now), 1.0],
                [_iso(now + timedelta(hours=1)), 2.0],
            ],
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert Observation.objects.filter(datastream=datastream).count() == 2


def test_insert_observations_append_mode_succeeds(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    end_time = timezone.now() - timedelta(days=1)
    ObservationFactory(datastream=datastream, phenomenon_time=end_time)
    datastream.phenomenon_end_time = end_time
    datastream.save(update_fields=["phenomenon_end_time"])
    new_time = end_time + timedelta(hours=1)
    client.force_login(owner)

    response = client.post(
        f"{_observations_url(datastream.id)}/bulk-create?mode=append",
        data={"fields": ["phenomenonTime", "result"], "data": [[_iso(new_time), 2.0]]},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert Observation.objects.filter(
        datastream=datastream, phenomenon_time=new_time
    ).exists()


def test_insert_observations_append_mode_returns_400_when_not_after_end_time(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    end_time = timezone.now()
    ObservationFactory(datastream=datastream, phenomenon_time=end_time)
    datastream.phenomenon_end_time = end_time
    datastream.save(update_fields=["phenomenon_end_time"])
    client.force_login(owner)

    response = client.post(
        f"{_observations_url(datastream.id)}/bulk-create?mode=append",
        data={"fields": ["phenomenonTime", "result"], "data": [[_iso(end_time), 2.0]]},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_insert_observations_backfill_mode_succeeds(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    begin_time = timezone.now()
    ObservationFactory(datastream=datastream, phenomenon_time=begin_time)
    datastream.phenomenon_begin_time = begin_time
    datastream.save(update_fields=["phenomenon_begin_time"])
    earlier_time = begin_time - timedelta(hours=1)
    client.force_login(owner)

    response = client.post(
        f"{_observations_url(datastream.id)}/bulk-create?mode=backfill",
        data={
            "fields": ["phenomenonTime", "result"],
            "data": [[_iso(earlier_time), 2.0]],
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert Observation.objects.filter(
        datastream=datastream, phenomenon_time=earlier_time
    ).exists()


def test_insert_observations_backfill_mode_returns_400_when_not_before_begin_time(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    begin_time = timezone.now()
    ObservationFactory(datastream=datastream, phenomenon_time=begin_time)
    datastream.phenomenon_begin_time = begin_time
    datastream.save(update_fields=["phenomenon_begin_time"])
    client.force_login(owner)

    response = client.post(
        f"{_observations_url(datastream.id)}/bulk-create?mode=backfill",
        data={
            "fields": ["phenomenonTime", "result"],
            "data": [[_iso(begin_time), 2.0]],
        },
        content_type="application/json",
    )

    assert response.status_code == 400


def test_insert_observations_replace_mode_succeeds(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    existing_time = timezone.now()
    ObservationFactory(datastream=datastream, phenomenon_time=existing_time, result=1.0)
    client.force_login(owner)

    response = client.post(
        f"{_observations_url(datastream.id)}/bulk-create?mode=replace",
        data={
            "fields": ["phenomenonTime", "result"],
            "data": [[_iso(existing_time), 42.0]],
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    observations = Observation.objects.filter(datastream=datastream)
    assert observations.count() == 1
    assert observations.get().result == 42.0


def test_insert_observations_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    collaborator = _collaborator_blocking_edit(workspace)
    client.force_login(collaborator.user)

    response = client.post(
        f"{_observations_url(datastream.id)}/bulk-create?mode=insert",
        data={
            "fields": ["phenomenonTime", "result"],
            "data": [[_iso(timezone.now()), 1.0]],
        },
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_observations (bulk-delete) --------------------------------------------------


def test_delete_observations_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    keep_time = timezone.now()
    remove_time = keep_time - timedelta(days=1)
    ObservationFactory(datastream=datastream, phenomenon_time=keep_time)
    ObservationFactory(datastream=datastream, phenomenon_time=remove_time)
    client.force_login(owner)

    response = client.post(
        f"{_observations_url(datastream.id)}/bulk-delete",
        data={
            "phenomenonTimeStart": _iso(remove_time),
            "phenomenonTimeEnd": _iso(remove_time),
        },
        content_type="application/json",
    )

    assert response.status_code == 204
    remaining = Observation.objects.filter(datastream=datastream)
    assert remaining.count() == 1
    assert remaining.get().phenomenon_time == keep_time


def test_delete_observations_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    observation = ObservationFactory(datastream=datastream)
    collaborator = _collaborator_blocking_edit(workspace)
    client.force_login(collaborator.user)

    response = client.post(
        f"{_observations_url(datastream.id)}/bulk-delete",
        data={"phenomenonTimeStart": _iso(observation.phenomenon_time)},
        content_type="application/json",
    )

    assert response.status_code == 403
