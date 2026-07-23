import pytest

from core.sta.models import MethodType, SensorEncodingType
from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, SensorFactory

pytestmark = pytest.mark.django_db

SENSORS_URL = "/api/data/sensors"


def _detail_url(sensor_id):
    return f"{SENSORS_URL}/{sensor_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Sensor", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _sensor_body(**overrides):
    body = {
        "name": "New Sensor",
        "description": "A new sensor.",
        "encodingType": "application/json",
        "methodType": "Instrument deployment",
    }
    body.update(overrides)
    return body


# --- get_sensors ------------------------------------------------------------------


def test_get_sensors_includes_global_sensors_for_anonymous(client):
    sensor = SensorFactory(global_=True)

    response = client.get(SENSORS_URL)

    assert response.status_code == 200
    assert str(sensor.id) in [s["id"] for s in response.json()]


def test_get_sensors_excludes_private_workspace_sensors_for_outsider(client):
    workspace = WorkspaceFactory(is_private=True)
    SensorFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(SENSORS_URL)

    assert response.json() == []


def test_get_sensors_includes_workspace_sensors_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    sensor = SensorFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(SENSORS_URL)

    assert response.status_code == 200
    assert str(sensor.id) in [s["id"] for s in response.json()]


# --- create_sensor ------------------------------------------------------------------


def test_create_sensor_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        SENSORS_URL,
        data=_sensor_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["name"] == "New Sensor"


def test_create_sensor_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        SENSORS_URL,
        data=_sensor_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_sensor_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        SENSORS_URL,
        data=_sensor_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 403


# --- get_sensor_encoding_types / get_method_types ------------------------------------


def test_get_sensor_encoding_types_returns_registered_type_names(client):
    SensorEncodingType.objects.create(name="application/json")
    SensorEncodingType.objects.create(name="application/geo+json")

    response = client.get(f"{SENSORS_URL}/encoding-types")

    assert response.status_code == 200
    assert set(response.json()) == {"application/json", "application/geo+json"}


def test_get_method_types_returns_registered_type_names(client):
    MethodType.objects.create(name="Instrument deployment")
    MethodType.objects.create(name="Estimation")

    response = client.get(f"{SENSORS_URL}/method-types")

    assert response.status_code == 200
    assert set(response.json()) == {"Instrument deployment", "Estimation"}


# --- get_sensor --------------------------------------------------------------------


def test_get_sensor_returns_global_sensor_for_anonymous(client):
    sensor = SensorFactory(global_=True)

    response = client.get(_detail_url(sensor.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(sensor.id)


def test_get_sensor_returns_404_for_private_workspace_sensor_when_unrelated(client):
    workspace = WorkspaceFactory(is_private=True)
    sensor = SensorFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(sensor.id))

    assert response.status_code == 404


def test_get_sensor_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    sensor = SensorFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(sensor.id))

    assert response.status_code == 200


def test_get_sensor_returns_404_for_nonexistent_sensor(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- update_sensor ------------------------------------------------------------------


def test_update_sensor_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    sensor = SensorFactory(workspace=workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(sensor.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_update_sensor_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    sensor = SensorFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(sensor.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_sensor ------------------------------------------------------------------


def test_delete_sensor_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    sensor = SensorFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(sensor.id))

    assert response.status_code == 204
    assert client.get(_detail_url(sensor.id)).status_code == 404


def test_delete_sensor_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    sensor = SensorFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(sensor.id))

    assert response.status_code == 403


def test_delete_sensor_returns_409_when_in_use_by_datastream(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    sensor = SensorFactory(workspace=workspace)
    DatastreamFactory(sensor=sensor)
    client.force_login(owner)

    response = client.delete(_detail_url(sensor.id))

    assert response.status_code == 409
