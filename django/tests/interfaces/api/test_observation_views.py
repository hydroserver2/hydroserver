from datetime import timedelta
from urllib.parse import urlencode

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
from tests.core.sta.factories import DatastreamFactory, ObservationFactory, MonitoringSiteFactory

pytestmark = pytest.mark.django_db


def _observations_url(datastream_id=None, **params):
    query = dict(params)
    if datastream_id is not None:
        query["datastream_id"] = datastream_id
    if query:
        return f"/api/data/observations?{urlencode(query, doseq=True)}"
    return "/api/data/observations"


def _detail_url(observation_id):
    return f"/api/data/observations/{observation_id}"


_BULK_CREATE_URL = "/api/data/observations/bulk-create"
_BULK_DELETE_URL = "/api/data/observations/bulk-delete"


def _with_datastream(datastream_id, body):
    return {**body, "datastreamId": str(datastream_id)}


def _make_datastream(workspace, **kwargs):
    return DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=workspace), **kwargs)


def _collaborator_without_observation_permissions(workspace):
    """A collaborator who can view the datastream but holds no Observation
    permissions, blocking every write action on its observations."""

    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Datastream", can_view=True)
    return CollaboratorFactory(workspace=workspace, role=role)


def _data_loader_collaborator(workspace, can_create=False, can_delete=False):
    """A collaborator shaped like the default Data Loader role: can view (but
    not edit) the datastream, plus specific Observation permissions -- the
    shape that should be able to push/remove data without datastream edit
    access."""

    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Datastream", can_view=True)
    PermissionFactory(
        role=role,
        resource_type="Observation",
        can_view=True,
        can_create=can_create,
        can_delete=can_delete,
    )
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
    assert str(observation.id) in [o["id"] for o in response.json()["data"]]


def test_get_observations_excludes_private_datastream_observation_when_outsider(client):
    """Filtering by a datastream_id the caller can't view now returns an
    empty page instead of 404, matching every other flat, filterable
    resource in this API (e.g. MonitoringSiteAPIService.list)."""
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace, private=True)
    ObservationFactory(datastream=datastream)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_observations_url(datastream.id))

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_get_observations_includes_observation_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace, private=True)
    observation = ObservationFactory(datastream=datastream)
    client.force_login(owner)

    response = client.get(_observations_url(datastream.id))

    assert response.status_code == 200
    assert str(observation.id) in [o["id"] for o in response.json()["data"]]


def test_get_observations_with_no_datastream_id_spans_viewable_datastreams(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream_a = _make_datastream(workspace)
    datastream_b = _make_datastream(workspace)
    observation_a = ObservationFactory(datastream=datastream_a)
    observation_b = ObservationFactory(datastream=datastream_b)
    client.force_login(owner)

    response = client.get(_observations_url())

    assert response.status_code == 200
    ids = [o["id"] for o in response.json()["data"]]
    assert str(observation_a.id) in ids
    assert str(observation_b.id) in ids


def test_get_observations_with_multiple_datastream_ids_unions_results(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream_a = _make_datastream(workspace)
    datastream_b = _make_datastream(workspace)
    other_datastream = _make_datastream(workspace)
    observation_a = ObservationFactory(datastream=datastream_a)
    observation_b = ObservationFactory(datastream=datastream_b)
    ObservationFactory(datastream=other_datastream)
    client.force_login(owner)

    response = client.get(
        f"/api/data/observations?{urlencode({'datastream_id': [str(datastream_a.id), str(datastream_b.id)]}, doseq=True)}"
    )

    assert response.status_code == 200
    ids = [o["id"] for o in response.json()["data"]]
    assert str(observation_a.id) in ids
    assert str(observation_b.id) in ids
    assert len(ids) == 2


def test_get_observations_row_format_returns_field_rows(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    ObservationFactory(datastream=datastream, result=99.5)

    response = client.get(_observations_url(datastream.id, format="row"))

    assert response.status_code == 200
    body = response.json()
    assert "phenomenonTime" in body["fields"]
    assert any(row[1] == 99.5 for row in body["data"])


def test_get_observations_column_format_returns_columnar_data(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    ObservationFactory(datastream=datastream, result=99.5)

    response = client.get(_observations_url(datastream.id, format="column"))

    assert response.status_code == 200
    assert 99.5 in response.json()["result"]


def test_get_observations_row_format_returns_400_without_datastream_id(client):
    response = client.get(_observations_url(format="row"))

    assert response.status_code == 400


def test_get_observations_column_format_returns_400_with_multiple_datastream_ids(client):
    workspace = WorkspaceFactory()
    datastream_a = _make_datastream(workspace)
    datastream_b = _make_datastream(workspace)

    response = client.get(
        f"/api/data/observations?{urlencode({'datastream_id': [str(datastream_a.id), str(datastream_b.id)], 'format': 'column'}, doseq=True)}"
    )

    assert response.status_code == 400


def test_get_observations_total_count_exact_for_no_filter(client):
    """Unfiltered total_count comes from summing Datastream.value_count, not a
    COUNT(*) over Observation -- confirm it matches the real row count."""
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream_a = _make_datastream(workspace)
    datastream_b = _make_datastream(workspace)
    ObservationFactory.create_batch(2, datastream=datastream_a)
    ObservationFactory.create_batch(3, datastream=datastream_b)
    datastream_a.value_count = 2
    datastream_a.save(update_fields=["value_count"])
    datastream_b.value_count = 3
    datastream_b.save(update_fields=["value_count"])
    client.force_login(owner)

    response = client.get(_observations_url())

    assert response.status_code == 200
    assert response.json()["meta"]["totalCount"] == 5


def test_get_observations_total_count_exact_for_datastream_id_filter(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream_a = _make_datastream(workspace)
    datastream_b = _make_datastream(workspace)
    ObservationFactory.create_batch(2, datastream=datastream_a)
    ObservationFactory.create_batch(3, datastream=datastream_b)
    datastream_a.value_count = 2
    datastream_a.save(update_fields=["value_count"])
    datastream_b.value_count = 3
    datastream_b.save(update_fields=["value_count"])
    client.force_login(owner)

    response = client.get(_observations_url(datastream_a.id))

    assert response.status_code == 200
    assert response.json()["meta"]["totalCount"] == 2


def test_get_observations_total_count_exact_for_phenomenon_time_filter(client):
    """A phenomenon_time filter isn't reflected in value_count, so this exercises
    the EXPLAIN-estimate/real-count path (resolve_count) instead -- on this small
    test dataset it should still resolve to an exact count."""
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    keep_time = timezone.now()
    excluded_time = keep_time - timedelta(days=1)
    ObservationFactory(datastream=datastream, phenomenon_time=keep_time)
    ObservationFactory(datastream=datastream, phenomenon_time=excluded_time)
    datastream.value_count = 2
    datastream.save(update_fields=["value_count"])
    client.force_login(owner)

    response = client.get(
        _observations_url(
            datastream.id, phenomenon_time_min=_iso(keep_time - timedelta(minutes=1))
        )
    )

    assert response.status_code == 200
    assert response.json()["meta"]["totalCount"] == 1


def test_get_observations_default_order_groups_by_datastream_then_time(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream_a = _make_datastream(workspace)
    datastream_b = _make_datastream(workspace)
    now = timezone.now()

    # Interleave phenomenon_time across datastreams so a pure time-only sort
    # would produce a different order than a (datastream_id, time) sort.
    a1 = ObservationFactory(datastream=datastream_a, phenomenon_time=now)
    b1 = ObservationFactory(datastream=datastream_b, phenomenon_time=now + timedelta(minutes=1))
    a2 = ObservationFactory(datastream=datastream_a, phenomenon_time=now + timedelta(minutes=2))
    b2 = ObservationFactory(datastream=datastream_b, phenomenon_time=now + timedelta(minutes=3))
    client.force_login(owner)

    response = client.get(
        f"/api/data/observations?{urlencode({'datastream_id': [str(datastream_a.id), str(datastream_b.id)]}, doseq=True)}"
    )

    assert response.status_code == 200
    ids = [o["id"] for o in response.json()["data"]]
    expected_order = [str(o.id) for o in sorted(
        [a1, b1, a2, b2], key=lambda o: (str(o.datastream_id), o.phenomenon_time)
    )]
    assert ids == expected_order


# --- create_observation ----------------------------------------------------------------


def test_create_observation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.post(
        _observations_url(),
        data=_with_datastream(
            datastream.id, {"phenomenonTime": _iso(timezone.now()), "result": 12.3}
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["result"] == 12.3


def test_create_observation_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)

    response = client.post(
        _observations_url(),
        data=_with_datastream(
            datastream.id, {"phenomenonTime": _iso(timezone.now()), "result": 12.3}
        ),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_observation_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    collaborator = _collaborator_without_observation_permissions(workspace)
    client.force_login(collaborator.user)

    response = client.post(
        _observations_url(),
        data=_with_datastream(
            datastream.id, {"phenomenonTime": _iso(timezone.now()), "result": 12.3}
        ),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_observation_succeeds_with_datastream_view_only_and_observation_create_permission(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    collaborator = _data_loader_collaborator(workspace, can_create=True)
    client.force_login(collaborator.user)

    response = client.post(
        _observations_url(),
        data=_with_datastream(
            datastream.id, {"phenomenonTime": _iso(timezone.now()), "result": 12.3}
        ),
        content_type="application/json",
    )

    assert response.status_code == 201


def test_create_observation_returns_422_for_duplicate_phenomenon_time(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    phenomenon_time = timezone.now()
    ObservationFactory(datastream=datastream, phenomenon_time=phenomenon_time)
    client.force_login(owner)

    response = client.post(
        _observations_url(),
        data=_with_datastream(
            datastream.id, {"phenomenonTime": _iso(phenomenon_time), "result": 12.3}
        ),
        content_type="application/json",
    )

    assert response.status_code == 422


def test_create_observation_returns_400_for_invalid_result_qualifier_code(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    client.force_login(owner)

    response = client.post(
        _observations_url(),
        data=_with_datastream(
            datastream.id,
            {
                "phenomenonTime": _iso(timezone.now()),
                "result": 12.3,
                "resultQualifierCodes": ["BOGUS"],
            },
        ),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_observation_returns_422_without_datastream_id(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    _make_datastream(workspace)
    client.force_login(owner)

    response = client.post(
        _observations_url(),
        data={"phenomenonTime": _iso(timezone.now()), "result": 12.3},
        content_type="application/json",
    )

    assert response.status_code == 422


# --- get_observation -------------------------------------------------------------------


def test_get_observation_returns_public_observation_for_anonymous(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    observation = ObservationFactory(datastream=datastream)

    response = client.get(_detail_url(observation.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(observation.id)


def test_get_observation_returns_404_for_private_datastream_observation_when_outsider(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace, private=True)
    observation = ObservationFactory(datastream=datastream)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(observation.id))

    assert response.status_code == 404


def test_get_observation_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace, private=True)
    observation = ObservationFactory(datastream=datastream)
    client.force_login(owner)

    response = client.get(_detail_url(observation.id))

    assert response.status_code == 200


def test_get_observation_returns_404_for_nonexistent_observation(client):
    response = client.get(
        _detail_url("00000000-0000-0000-0000-000000000000")
    )

    assert response.status_code == 404


# --- delete_observation ----------------------------------------------------------------


def test_delete_observation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    observation = ObservationFactory(datastream=datastream)
    client.force_login(owner)

    response = client.delete(_detail_url(observation.id))

    assert response.status_code == 204
    assert client.get(_detail_url(observation.id)).status_code == 404


def test_delete_observation_updates_datastream_statistics(client):
    """Regression test for the delete() fix: datastream is now derived from
    the already-resolved Observation instead of a second lookup keyed on a
    datastream_id that's no longer supplied."""
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    keep_time = timezone.now()
    remove_time = keep_time - timedelta(days=1)
    ObservationFactory(datastream=datastream, phenomenon_time=keep_time)
    observation = ObservationFactory(datastream=datastream, phenomenon_time=remove_time)
    datastream.phenomenon_begin_time = remove_time
    datastream.phenomenon_end_time = keep_time
    datastream.save(update_fields=["phenomenon_begin_time", "phenomenon_end_time"])
    client.force_login(owner)

    response = client.delete(_detail_url(observation.id))

    assert response.status_code == 204
    datastream.refresh_from_db()
    assert datastream.phenomenon_begin_time == keep_time


def test_delete_observation_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    observation = ObservationFactory(datastream=datastream)
    collaborator = _collaborator_without_observation_permissions(workspace)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(observation.id))

    assert response.status_code == 403


def test_delete_observation_succeeds_with_datastream_view_only_and_observation_delete_permission(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    observation = ObservationFactory(datastream=datastream)
    collaborator = _data_loader_collaborator(workspace, can_delete=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(observation.id))

    assert response.status_code == 204


# --- insert_observations (bulk-create) --------------------------------------------------


def test_insert_observations_insert_mode_succeeds(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    now = timezone.now()
    client.force_login(owner)

    response = client.post(
        f"{_BULK_CREATE_URL}?mode=insert",
        data=_with_datastream(
            datastream.id,
            {
                "fields": ["phenomenonTime", "result"],
                "data": [
                    [_iso(now), 1.0],
                    [_iso(now + timedelta(hours=1)), 2.0],
                ],
            },
        ),
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
        f"{_BULK_CREATE_URL}?mode=append",
        data=_with_datastream(
            datastream.id,
            {"fields": ["phenomenonTime", "result"], "data": [[_iso(new_time), 2.0]]},
        ),
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
        f"{_BULK_CREATE_URL}?mode=append",
        data=_with_datastream(
            datastream.id,
            {"fields": ["phenomenonTime", "result"], "data": [[_iso(end_time), 2.0]]},
        ),
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
        f"{_BULK_CREATE_URL}?mode=backfill",
        data=_with_datastream(
            datastream.id,
            {
                "fields": ["phenomenonTime", "result"],
                "data": [[_iso(earlier_time), 2.0]],
            },
        ),
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
        f"{_BULK_CREATE_URL}?mode=backfill",
        data=_with_datastream(
            datastream.id,
            {
                "fields": ["phenomenonTime", "result"],
                "data": [[_iso(begin_time), 2.0]],
            },
        ),
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
        f"{_BULK_CREATE_URL}?mode=replace",
        data=_with_datastream(
            datastream.id,
            {
                "fields": ["phenomenonTime", "result"],
                "data": [[_iso(existing_time), 42.0]],
            },
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    observations = Observation.objects.filter(datastream=datastream)
    assert observations.count() == 1
    assert observations.get().result == 42.0


def test_insert_observations_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    collaborator = _collaborator_without_observation_permissions(workspace)
    client.force_login(collaborator.user)

    response = client.post(
        f"{_BULK_CREATE_URL}?mode=insert",
        data=_with_datastream(
            datastream.id,
            {
                "fields": ["phenomenonTime", "result"],
                "data": [[_iso(timezone.now()), 1.0]],
            },
        ),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_insert_observations_succeeds_with_datastream_view_only_and_observation_create_permission(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    collaborator = _data_loader_collaborator(workspace, can_create=True)
    client.force_login(collaborator.user)

    response = client.post(
        f"{_BULK_CREATE_URL}?mode=insert",
        data=_with_datastream(
            datastream.id,
            {
                "fields": ["phenomenonTime", "result"],
                "data": [[_iso(timezone.now()), 1.0]],
            },
        ),
        content_type="application/json",
    )

    assert response.status_code == 201


def test_insert_observations_returns_422_without_datastream_id(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    _make_datastream(workspace)
    client.force_login(owner)

    response = client.post(
        f"{_BULK_CREATE_URL}?mode=insert",
        data={
            "fields": ["phenomenonTime", "result"],
            "data": [[_iso(timezone.now()), 1.0]],
        },
        content_type="application/json",
    )

    assert response.status_code == 422


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
        _BULK_DELETE_URL,
        data=_with_datastream(
            datastream.id,
            {
                "phenomenonTimeStart": _iso(remove_time),
                "phenomenonTimeEnd": _iso(remove_time),
            },
        ),
        content_type="application/json",
    )

    assert response.status_code == 204
    remaining = Observation.objects.filter(datastream=datastream)
    assert remaining.count() == 1
    assert remaining.get().phenomenon_time == keep_time


def test_delete_observations_returns_403_without_delete_permission(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    observation = ObservationFactory(datastream=datastream)
    collaborator = _collaborator_without_observation_permissions(workspace)
    client.force_login(collaborator.user)

    response = client.post(
        _BULK_DELETE_URL,
        data=_with_datastream(
            datastream.id, {"phenomenonTimeStart": _iso(observation.phenomenon_time)}
        ),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_delete_observations_succeeds_with_datastream_view_only_and_observation_delete_permission(client):
    workspace = WorkspaceFactory()
    datastream = _make_datastream(workspace)
    observation = ObservationFactory(datastream=datastream)
    collaborator = _data_loader_collaborator(workspace, can_delete=True)
    client.force_login(collaborator.user)

    response = client.post(
        _BULK_DELETE_URL,
        data=_with_datastream(
            datastream.id, {"phenomenonTimeStart": _iso(observation.phenomenon_time)}
        ),
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not Observation.objects.filter(pk=observation.pk).exists()


def test_delete_observations_returns_422_without_datastream_id(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    datastream = _make_datastream(workspace)
    observation = ObservationFactory(datastream=datastream)
    client.force_login(owner)

    response = client.post(
        _BULK_DELETE_URL,
        data={"phenomenonTimeStart": _iso(observation.phenomenon_time)},
        content_type="application/json",
    )

    assert response.status_code == 422
