import pytest

from django.test.utils import CaptureQueriesContext
from django.db import connection

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory
from tests.processing.etl.factories import EtlTaskFactory, EtlMappingFactory

pytestmark = pytest.mark.django_db

MAPPINGS_URL = "/api/data/etl-mappings"

MAPPING_FIELDS = {"id", "sourceIdentifier", "targetDatastreamId", "etlTaskId"}


def _detail_url(mapping_id):
    return f"{MAPPINGS_URL}/{mapping_id}"


def _collaborator_with_permission(workspace, resource_type="EtlTask", **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type=resource_type, **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _collaborator_who_can_create_mappings(workspace):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="EtlTask", can_view=True)
    PermissionFactory(role=role, resource_type="EtlMapping", can_create=True)
    PermissionFactory(role=role, resource_type="Datastream", can_edit=True)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_task(workspace):
    return EtlTaskFactory(data_connection__workspace=workspace)


def _make_mapping(task, **kwargs):
    monitoring_site = MonitoringSiteFactory(workspace=task.data_connection.workspace)
    target = DatastreamFactory(monitoring_site=monitoring_site)
    return EtlMappingFactory(etl_task=task, target_datastream=target, **kwargs)


# --- get_etl_mappings --------------------------------------------------------------


def test_get_etl_mappings_includes_mapping_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_task(workspace)
    mapping = _make_mapping(task)
    client.force_login(owner)

    response = client.get(MAPPINGS_URL, {"etl_task_id": str(task.id)})

    assert response.status_code == 200
    body = response.json()
    assert str(mapping.id) in [m["id"] for m in body["data"]]
    assert set(body["data"][0].keys()) == MAPPING_FIELDS
    assert body["data"][0]["etlTaskId"] == str(task.id)


def test_get_etl_mappings_filters_by_workspace_id(client):
    owner = UserFactory()
    workspace_a = WorkspaceFactory(owner=owner)
    workspace_b = WorkspaceFactory(owner=owner)
    task_a = _make_task(workspace_a)
    task_b = _make_task(workspace_b)
    mapping_a = _make_mapping(task_a)
    _make_mapping(task_b)
    client.force_login(owner)

    response = client.get(MAPPINGS_URL, {"workspace_id": str(workspace_a.id)})

    assert response.status_code == 200
    assert [m["id"] for m in response.json()["data"]] == [str(mapping_a.id)]


def test_get_etl_mappings_excludes_mappings_outside_outsiders_workspaces(client):
    workspace = WorkspaceFactory()
    task = _make_task(workspace)
    _make_mapping(task)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(MAPPINGS_URL, {"workspace_id": str(workspace.id)})

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_get_etl_mappings_returns_401_when_unauthenticated(client):
    response = client.get(MAPPINGS_URL)

    assert response.status_code == 401


# --- create_etl_mapping -------------------------------------------------------------


def test_create_etl_mapping_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_task(workspace)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    target = DatastreamFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.post(
        MAPPINGS_URL,
        data={
            "etlTaskId": str(task.id),
            "sourceIdentifier": "col_a",
            "targetDatastreamId": str(target.id),
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    mapping_id = response.json()["id"]

    detail = client.get(_detail_url(mapping_id))
    assert detail.json()["data"]["sourceIdentifier"] == "col_a"
    assert detail.json()["data"]["targetDatastreamId"] == str(target.id)
    assert detail.json()["data"]["etlTaskId"] == str(task.id)


def test_create_etl_mapping_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    task = _make_task(workspace)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    target = DatastreamFactory(monitoring_site=monitoring_site)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        MAPPINGS_URL,
        data={
            "etlTaskId": str(task.id),
            "sourceIdentifier": "col_a",
            "targetDatastreamId": str(target.id),
        },
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_etl_mapping_succeeds_for_collaborator_with_create_permission(client):
    workspace = WorkspaceFactory()
    task = _make_task(workspace)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    target = DatastreamFactory(monitoring_site=monitoring_site)
    collaborator = _collaborator_who_can_create_mappings(workspace)
    client.force_login(collaborator.user)

    response = client.post(
        MAPPINGS_URL,
        data={
            "etlTaskId": str(task.id),
            "sourceIdentifier": "col_a",
            "targetDatastreamId": str(target.id),
        },
        content_type="application/json",
    )

    assert response.status_code == 201


def test_create_etl_mapping_returns_404_for_nonexistent_task(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    target = DatastreamFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.post(
        MAPPINGS_URL,
        data={
            "etlTaskId": "00000000-0000-0000-0000-000000000000",
            "sourceIdentifier": "col_a",
            "targetDatastreamId": str(target.id),
        },
        content_type="application/json",
    )

    assert response.status_code == 404


def test_create_etl_mapping_returns_400_for_duplicate_target_datastream(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_task(workspace)
    existing = _make_mapping(task)
    client.force_login(owner)

    response = client.post(
        MAPPINGS_URL,
        data={
            "etlTaskId": str(task.id),
            "sourceIdentifier": "col_b",
            "targetDatastreamId": str(existing.target_datastream_id),
        },
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_etl_mapping --------------------------------------------------------------


def test_get_etl_mapping_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_task(workspace)
    mapping = _make_mapping(task)
    client.force_login(owner)

    response = client.get(_detail_url(mapping.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(mapping.id)


def test_get_etl_mapping_returns_404_for_nonexistent_mapping(client):
    owner = UserFactory()
    WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_etl_mapping_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    task = _make_task(workspace)
    mapping = _make_mapping(task)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(mapping.id))

    assert response.status_code == 404


def test_get_etl_mapping_include_sideloads_target_datastream(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_task(workspace)
    mapping = _make_mapping(task)
    client.force_login(owner)

    response = client.get(_detail_url(mapping.id), {"include": "targetDatastream"})

    assert response.status_code == 200
    body = response.json()
    assert {row["id"] for row in body["included"]["targetDatastreams"]} == {
        str(mapping.target_datastream_id)
    }


def test_get_etl_mappings_include_does_not_scale_queries_with_mapping_count(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_task(workspace)
    for _ in range(5):
        _make_mapping(task)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(
            MAPPINGS_URL, {"etl_task_id": str(task.id), "include": "targetDatastream"}
        )

    for _ in range(5):
        _make_mapping(task)

    with CaptureQueriesContext(connection) as large:
        client.get(
            MAPPINGS_URL, {"etl_task_id": str(task.id), "include": "targetDatastream"}
        )

    assert len(large.captured_queries) == len(small.captured_queries)


# --- update_etl_mapping -------------------------------------------------------------


def test_update_etl_mapping_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_task(workspace)
    mapping = _make_mapping(task, source_identifier="old_col")
    client.force_login(owner)

    response = client.patch(
        _detail_url(mapping.id),
        data={"sourceIdentifier": "new_col"},
        content_type="application/json",
    )

    assert response.status_code == 204

    detail = client.get(_detail_url(mapping.id))
    assert detail.json()["data"]["sourceIdentifier"] == "new_col"


def test_update_etl_mapping_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    task = _make_task(workspace)
    mapping = _make_mapping(task)
    collaborator = _collaborator_with_permission(
        workspace, resource_type="EtlMapping", can_view=True
    )
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(mapping.id),
        data={"sourceIdentifier": "new_col"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_etl_mapping -------------------------------------------------------------


def test_delete_etl_mapping_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task = _make_task(workspace)
    mapping = _make_mapping(task)
    client.force_login(owner)

    response = client.delete(_detail_url(mapping.id))

    assert response.status_code == 204
    assert client.get(_detail_url(mapping.id)).status_code == 404


def test_delete_etl_mapping_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task = _make_task(workspace)
    mapping = _make_mapping(task)
    collaborator = _collaborator_with_permission(
        workspace, resource_type="EtlMapping", can_view=True
    )
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(mapping.id))

    assert response.status_code == 403
