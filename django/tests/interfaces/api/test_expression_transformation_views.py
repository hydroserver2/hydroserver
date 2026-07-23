import pytest

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, ThingFactory
from tests.processing.products.factories import (
    DataProductTaskFactory,
    DataProductTransformationFactory,
    DataProductTransformationInputFactory,
)

pytestmark = pytest.mark.django_db

DATA_PRODUCT_TASKS_URL = "/api/data/products/tasks"


def _transformations_url(task_id):
    return f"{DATA_PRODUCT_TASKS_URL}/{task_id}/transformations/expression"


def _detail_url(task_id, transformation_id):
    return f"{_transformations_url(task_id)}/{transformation_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="DataProductTask", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_task_with_thing(workspace):
    thing = ThingFactory(workspace=workspace)
    task = DataProductTaskFactory(thing=thing)
    return task, thing


def _make_transformation(task, thing):
    output_ds = DatastreamFactory(thing=thing)
    input_ds = DatastreamFactory(thing=thing)
    transformation = DataProductTransformationFactory(
        task=task,
        output_datastream=output_ds,
        transformation_type="expression",
        formula="x",
    )
    DataProductTransformationInputFactory(
        transformation=transformation, datastream=input_ds, variable_name="x"
    )
    return transformation


def _transformation_body(output_ds, input_ds, **overrides):
    body = {
        "outputDatastreamId": str(output_ds.id),
        "inputDatastreamId": str(input_ds.id),
        "variableName": "x",
        "formula": "x",
    }
    body.update(overrides)
    return body


# --- get_expression_transformations -----------------------------------------------------


def test_get_expression_transformations_includes_transformation_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, thing = _make_task_with_thing(workspace)
    transformation = _make_transformation(task, thing)
    client.force_login(owner)

    response = client.get(_transformations_url(task.id))

    assert response.status_code == 200
    assert str(transformation.id) in [t["id"] for t in response.json()]


def test_get_expression_transformations_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    task, thing = _make_task_with_thing(workspace)
    _make_transformation(task, thing)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_transformations_url(task.id))

    assert response.status_code == 404


def test_get_expression_transformations_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    task, thing = _make_task_with_thing(workspace)

    response = client.get(_transformations_url(task.id))

    assert response.status_code == 401


# --- create_expression_transformation ---------------------------------------------------


def test_create_expression_transformation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, thing = _make_task_with_thing(workspace)
    output_ds = DatastreamFactory(thing=thing)
    input_ds = DatastreamFactory(thing=thing)
    client.force_login(owner)

    response = client.post(
        _transformations_url(task.id),
        data=_transformation_body(output_ds, input_ds),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["formula"] == "x"


def test_create_expression_transformation_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    task, thing = _make_task_with_thing(workspace)
    output_ds = DatastreamFactory(thing=thing)
    input_ds = DatastreamFactory(thing=thing)

    response = client.post(
        _transformations_url(task.id),
        data=_transformation_body(output_ds, input_ds),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_expression_transformation_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    task, thing = _make_task_with_thing(workspace)
    output_ds = DatastreamFactory(thing=thing)
    input_ds = DatastreamFactory(thing=thing)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        _transformations_url(task.id),
        data=_transformation_body(output_ds, input_ds),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_expression_transformation_returns_400_for_invalid_formula(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, thing = _make_task_with_thing(workspace)
    output_ds = DatastreamFactory(thing=thing)
    input_ds = DatastreamFactory(thing=thing)
    client.force_login(owner)

    response = client.post(
        _transformations_url(task.id),
        data=_transformation_body(output_ds, input_ds, formula="y"),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_expression_transformation --------------------------------------------------------


def test_get_expression_transformation_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, thing = _make_task_with_thing(workspace)
    transformation = _make_transformation(task, thing)
    client.force_login(owner)

    response = client.get(_detail_url(task.id, transformation.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(transformation.id)


def test_get_expression_transformation_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    task, thing = _make_task_with_thing(workspace)
    transformation = _make_transformation(task, thing)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(task.id, transformation.id))

    assert response.status_code == 404


def test_get_expression_transformation_returns_404_for_nonexistent_transformation(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, _ = _make_task_with_thing(workspace)
    client.force_login(owner)

    response = client.get(
        _detail_url(task.id, "00000000-0000-0000-0000-000000000000")
    )

    assert response.status_code == 404


# --- update_expression_transformation --------------------------------------------------------


def test_update_expression_transformation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, thing = _make_task_with_thing(workspace)
    transformation = _make_transformation(task, thing)
    client.force_login(owner)

    response = client.patch(
        _detail_url(task.id, transformation.id),
        data={"formula": "x + 1"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["formula"] == "x + 1"


def test_update_expression_transformation_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task, thing = _make_task_with_thing(workspace)
    transformation = _make_transformation(task, thing)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(task.id, transformation.id),
        data={"formula": "x + 1"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_expression_transformation --------------------------------------------------------


def test_delete_expression_transformation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, thing = _make_task_with_thing(workspace)
    transformation = _make_transformation(task, thing)
    client.force_login(owner)

    response = client.delete(_detail_url(task.id, transformation.id))

    assert response.status_code == 204
    assert client.get(_detail_url(task.id, transformation.id)).status_code == 404


def test_delete_expression_transformation_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task, thing = _make_task_with_thing(workspace)
    transformation = _make_transformation(task, thing)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(task.id, transformation.id))

    assert response.status_code == 403
