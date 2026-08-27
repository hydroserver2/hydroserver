import pytest

from core.sta.models import VariableType
from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, ObservedPropertyFactory

pytestmark = pytest.mark.django_db

OBSERVED_PROPERTIES_URL = "/api/data/observed-properties"


def _detail_url(observed_property_id):
    return f"{OBSERVED_PROPERTIES_URL}/{observed_property_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="ObservedProperty", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _observed_property_body(**overrides):
    body = {
        "name": "New Observed Property",
        "definition": "https://example.com/def",
        "description": "A new observed property.",
        "type": "Hydrology",
        "code": "OP-NEW",
    }
    body.update(overrides)
    return body


# --- get_observed_properties ---------------------------------------------------------


def test_get_observed_properties_includes_global_properties_for_anonymous(client):
    observed_property = ObservedPropertyFactory(global_=True)

    response = client.get(OBSERVED_PROPERTIES_URL)

    assert response.status_code == 200
    assert str(observed_property.id) in [o["id"] for o in response.json()]


def test_get_observed_properties_excludes_private_workspace_properties_for_outsider(
    client,
):
    workspace = WorkspaceFactory(is_private=True)
    ObservedPropertyFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(OBSERVED_PROPERTIES_URL)

    assert response.json() == []


def test_get_observed_properties_includes_workspace_properties_for_workspace_owner(
    client,
):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(OBSERVED_PROPERTIES_URL)

    assert response.status_code == 200
    assert str(observed_property.id) in [o["id"] for o in response.json()]


def test_get_observed_properties_filters_by_type(client):
    hydrology = ObservedPropertyFactory(global_=True, type="Hydrology")
    ObservedPropertyFactory(global_=True, type="Meteorology")

    response = client.get(OBSERVED_PROPERTIES_URL, {"type": "Hydrology"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(hydrology.id)]


# --- create_observed_property ---------------------------------------------------------


def test_create_observed_property_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        OBSERVED_PROPERTIES_URL,
        data=_observed_property_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["name"] == "New Observed Property"
    assert response.json()["type"] == "Hydrology"


def test_create_observed_property_allows_omitting_definition(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)
    body = _observed_property_body(workspaceId=str(workspace.id))
    body.pop("definition")

    response = client.post(
        OBSERVED_PROPERTIES_URL,
        data=body,
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["definition"] is None


@pytest.mark.parametrize("field", ["type", "code"])
def test_create_observed_property_allows_500_character_type_and_code(client, field):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)
    value = "x" * 500

    response = client.post(
        OBSERVED_PROPERTIES_URL,
        data=_observed_property_body(
            workspaceId=str(workspace.id),
            **{field: value},
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()[field] == value


def test_create_observed_property_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        OBSERVED_PROPERTIES_URL,
        data=_observed_property_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_observed_property_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        OBSERVED_PROPERTIES_URL,
        data=_observed_property_body(workspaceId=str(workspace.id)),
        content_type="application/json",
    )

    assert response.status_code == 403


# --- get_datastream_aggregation_statistics (variable-types) ---------------------------


def test_get_variable_types_returns_registered_type_names(client):
    VariableType.objects.create(name="Hydrology")
    VariableType.objects.create(name="Meteorology")

    response = client.get(f"{OBSERVED_PROPERTIES_URL}/variable-types")

    assert response.status_code == 200
    assert set(response.json()) == {"Hydrology", "Meteorology"}


# --- get_observed_property -------------------------------------------------------------


def test_get_observed_property_returns_global_property_for_anonymous(client):
    observed_property = ObservedPropertyFactory(global_=True)

    response = client.get(_detail_url(observed_property.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(observed_property.id)


def test_get_observed_property_returns_404_for_private_workspace_property_when_unrelated(
    client,
):
    workspace = WorkspaceFactory(is_private=True)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(observed_property.id))

    assert response.status_code == 404


def test_get_observed_property_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(observed_property.id))

    assert response.status_code == 200


def test_get_observed_property_returns_404_for_nonexistent_property(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- update_observed_property -----------------------------------------------------------


def test_update_observed_property_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    observed_property = ObservedPropertyFactory(
        workspace=workspace, name="Original Name"
    )
    client.force_login(owner)

    response = client.patch(
        _detail_url(observed_property.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_update_observed_property_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    observed_property = ObservedPropertyFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(observed_property.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_observed_property -----------------------------------------------------------


def test_delete_observed_property_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(observed_property.id))

    assert response.status_code == 204
    assert client.get(_detail_url(observed_property.id)).status_code == 404


def test_delete_observed_property_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    observed_property = ObservedPropertyFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(observed_property.id))

    assert response.status_code == 403


def test_delete_observed_property_returns_409_when_in_use_by_datastream(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    observed_property = ObservedPropertyFactory(workspace=workspace)
    DatastreamFactory(observed_property=observed_property)
    client.force_login(owner)

    response = client.delete(_detail_url(observed_property.id))

    assert response.status_code == 409
