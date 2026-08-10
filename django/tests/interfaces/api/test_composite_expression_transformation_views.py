import pytest

from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory
from tests.processing.products.factories import (
    DataProductTaskFactory,
    DataProductTransformationFactory,
    DataProductTransformationInputFactory,
)

pytestmark = pytest.mark.django_db

DATA_PRODUCT_TASKS_URL = "/api/data/products/tasks"


def _transformations_url(task_id):
    return f"{DATA_PRODUCT_TASKS_URL}/{task_id}/transformations/composite-expression"


def _detail_url(task_id, transformation_id):
    return f"{_transformations_url(task_id)}/{transformation_id}"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="DataProductTask", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_task_with_monitoring_site(workspace):
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    task = DataProductTaskFactory(monitoring_site=monitoring_site)
    return task, monitoring_site


def _make_transformation(task, monitoring_site):
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds_a = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds_b = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task,
        output_datastream=output_ds,
        transformation_type="composite_expression",
        formula="a + b",
        output_interval_units="minutes",
        output_interval=15,
    )
    DataProductTransformationInputFactory(
        transformation=transformation, datastream=input_ds_a, variable_name="a"
    )
    DataProductTransformationInputFactory(
        transformation=transformation, datastream=input_ds_b, variable_name="b"
    )
    return transformation


def _transformation_body(output_ds, input_ds_a, input_ds_b, **overrides):
    body = {
        "outputDatastreamId": str(output_ds.id),
        "inputDatastreams": [
            {"datastreamId": str(input_ds_a.id), "variableName": "a"},
            {"datastreamId": str(input_ds_b.id), "variableName": "b"},
        ],
        "formula": "a + b",
        "outputIntervalUnits": "minutes",
        "outputInterval": 15,
    }
    body.update(overrides)
    return body


# --- get_composite_expression_transformations ---------------------------------------------


def test_get_composite_expression_transformations_includes_transformation_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(_transformations_url(task.id))

    assert response.status_code == 200
    assert str(transformation.id) in [t["id"] for t in response.json()]


def test_get_composite_expression_transformations_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    _make_transformation(task, monitoring_site)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_transformations_url(task.id))

    assert response.status_code == 404


def test_get_composite_expression_transformations_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)

    response = client.get(_transformations_url(task.id))

    assert response.status_code == 401


# --- create_composite_expression_transformation -------------------------------------------


def test_create_composite_expression_transformation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds_a = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds_b = DatastreamFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.post(
        _transformations_url(task.id),
        data=_transformation_body(output_ds, input_ds_a, input_ds_b),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["formula"] == "a + b"


def test_create_composite_expression_transformation_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds_a = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds_b = DatastreamFactory(monitoring_site=monitoring_site)

    response = client.post(
        _transformations_url(task.id),
        data=_transformation_body(output_ds, input_ds_a, input_ds_b),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_composite_expression_transformation_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds_a = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds_b = DatastreamFactory(monitoring_site=monitoring_site)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        _transformations_url(task.id),
        data=_transformation_body(output_ds, input_ds_a, input_ds_b),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_composite_expression_transformation_returns_400_for_single_input(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds_a = DatastreamFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    body = _transformation_body(output_ds, input_ds_a, input_ds_a)
    body["inputDatastreams"] = [{"datastreamId": str(input_ds_a.id), "variableName": "a"}]
    body["formula"] = "a"

    response = client.post(
        _transformations_url(task.id),
        data=body,
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_composite_expression_transformation --------------------------------------------------


def test_get_composite_expression_transformation_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(_detail_url(task.id, transformation.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(transformation.id)


def test_get_composite_expression_transformation_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_transformation(task, monitoring_site)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(task.id, transformation.id))

    assert response.status_code == 404


def test_get_composite_expression_transformation_returns_404_for_nonexistent_transformation(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, _ = _make_task_with_monitoring_site(workspace)
    client.force_login(owner)

    response = client.get(
        _detail_url(task.id, "00000000-0000-0000-0000-000000000000")
    )

    assert response.status_code == 404


# --- update_composite_expression_transformation --------------------------------------------------


def test_update_composite_expression_transformation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.patch(
        _detail_url(task.id, transformation.id),
        data={"outputInterval": 30},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["outputInterval"] == 30


def test_update_composite_expression_transformation_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_transformation(task, monitoring_site)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(task.id, transformation.id),
        data={"outputInterval": 30},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_composite_expression_transformation --------------------------------------------------


def test_delete_composite_expression_transformation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.delete(_detail_url(task.id, transformation.id))

    assert response.status_code == 204
    assert client.get(_detail_url(task.id, transformation.id)).status_code == 404


def test_delete_composite_expression_transformation_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_transformation(task, monitoring_site)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(task.id, transformation.id))

    assert response.status_code == 403
