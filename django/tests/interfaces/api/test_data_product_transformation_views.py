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
from tests.processing.products.factories import (
    DataProductTaskFactory,
    DataProductTransformationFactory,
    DataProductTransformationInputFactory,
    RatingCurveFactory,
)

pytestmark = pytest.mark.django_db

DATA_PRODUCT_TASKS_URL = "/api/data/products/tasks"

TRANSFORMATION_FIELDS = {
    "id",
    "transformationType",
    "outputDatastreamId",
    "inputDatastreams",
    "ratingCurveId",
    "formula",
    "aggregationMethod",
    "outputIntervalUnits",
    "outputInterval",
    "timezoneType",
    "timezone",
    "minValues",
    "stopOnNoData",
    "stopOnError",
}


def _transformations_url(task_id):
    return f"{DATA_PRODUCT_TASKS_URL}/{task_id}/transformations"


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


def _make_rating_curve_transformation(task, monitoring_site):
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds = DatastreamFactory(monitoring_site=monitoring_site)
    rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task,
        output_datastream=output_ds,
        transformation_type="rating_curve",
        formula=None,
        rating_curve=rating_curve,
    )
    DataProductTransformationInputFactory(transformation=transformation, datastream=input_ds)
    return transformation


def _rating_curve_body(output_ds, input_ds, rating_curve, **overrides):
    body = {
        "transformationType": "rating_curve",
        "outputDatastreamId": str(output_ds.id),
        "inputDatastreams": [{"datastreamId": str(input_ds.id)}],
        "ratingCurveId": str(rating_curve.id),
    }
    body.update(overrides)
    return body


def _derivation_body(output_ds, input_ds, **overrides):
    body = {
        "transformationType": "derivation",
        "outputDatastreamId": str(output_ds.id),
        "inputDatastreams": [{"datastreamId": str(input_ds.id), "variableName": "x"}],
        "formula": "x",
    }
    body.update(overrides)
    return body


def _aggregation_body(output_ds, input_ds, **overrides):
    body = {
        "transformationType": "aggregation",
        "outputDatastreamId": str(output_ds.id),
        "inputDatastreams": [{"datastreamId": str(input_ds.id)}],
        "aggregationMethod": "mean",
        "outputIntervalUnits": "hours",
        "outputInterval": 1,
    }
    body.update(overrides)
    return body


# --- get_data_product_transformations ---------------------------------------------------


def test_get_transformations_includes_transformation_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(_transformations_url(task.id))

    assert response.status_code == 200
    assert str(transformation.id) in [t["id"] for t in response.json()["data"]]


def test_get_transformations_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    _make_rating_curve_transformation(task, monitoring_site)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_transformations_url(task.id))

    assert response.status_code == 404


def test_get_transformations_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)

    response = client.get(_transformations_url(task.id))

    assert response.status_code == 401


def test_get_transformations_filters_by_transformation_type(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    rating_curve_transformation = _make_rating_curve_transformation(task, monitoring_site)
    DataProductTransformationFactory(
        task=task,
        output_datastream=DatastreamFactory(monitoring_site=monitoring_site),
        transformation_type="derivation",
        formula="x",
    )
    client.force_login(owner)

    response = client.get(_transformations_url(task.id), {"transformation_type": "rating_curve"})

    assert response.status_code == 200
    assert [t["id"] for t in response.json()["data"]] == [str(rating_curve_transformation.id)]


def test_get_transformations_properties_filters_every_item_in_the_list(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(
        _transformations_url(task.id), {"properties": "id,transformationType"}
    )

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    for item in items:
        assert set(item.keys()) == {"id", "transformationType"}


def test_get_transformations_properties_rejects_unknown_property(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, _ = _make_task_with_monitoring_site(workspace)
    client.force_login(owner)

    response = client.get(_transformations_url(task.id), {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_transformations_without_properties_returns_every_field(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(_transformations_url(task.id))

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == TRANSFORMATION_FIELDS


def test_get_transformations_has_no_included_key_without_include_param(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(_transformations_url(task.id))

    assert response.status_code == 200
    assert "included" not in response.json()


def test_get_transformations_include_output_datastream_and_rating_curve(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(
        _transformations_url(task.id), {"include": "outputDatastream,ratingCurve"}
    )

    assert response.status_code == 200
    body = response.json()
    assert [d["id"] for d in body["included"]["outputDatastreams"]] == [
        str(transformation.output_datastream_id)
    ]
    assert [r["id"] for r in body["included"]["ratingCurves"]] == [
        str(transformation.rating_curve_id)
    ]


def test_get_transformations_include_rejects_unknown_relation(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, _ = _make_task_with_monitoring_site(workspace)
    client.force_login(owner)

    response = client.get(_transformations_url(task.id), {"include": "bogus"})

    assert response.status_code == 400


def test_get_transformations_properties_and_include_together(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(
        _transformations_url(task.id),
        {"properties": "id,transformationType", "include": "outputDatastream"},
    )

    assert response.status_code == 200
    body = response.json()
    for item in body["data"]:
        assert set(item.keys()) == {"id", "transformationType"}
    assert body["included"]["outputDatastreams"][0]["id"] == str(
        transformation.output_datastream_id
    )


def test_get_transformations_include_does_not_scale_queries_with_transformation_count(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    for _ in range(5):
        _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    with CaptureQueriesContext(connection) as small:
        client.get(_transformations_url(task.id), {"include": "outputDatastream,ratingCurve"})

    for _ in range(5):
        _make_rating_curve_transformation(task, monitoring_site)

    with CaptureQueriesContext(connection) as large:
        client.get(_transformations_url(task.id), {"include": "outputDatastream,ratingCurve"})

    assert len(large.captured_queries) == len(small.captured_queries)


def test_get_transformations_sorts_by_output_datastream_id(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    t1 = _make_rating_curve_transformation(task, monitoring_site)
    t2 = _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(_transformations_url(task.id), {"sortby": "outputDatastreamId"})

    expected = sorted([str(t1.output_datastream_id), str(t2.output_datastream_id)])
    assert response.status_code == 200
    assert [t["outputDatastreamId"] for t in response.json()["data"]] == expected


def test_get_transformations_sortby_rejects_unknown_field(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, _ = _make_task_with_monitoring_site(workspace)
    client.force_login(owner)

    response = client.get(_transformations_url(task.id), {"sortby": "bogus"})

    assert response.status_code == 400


# --- create_data_product_transformation --------------------------------------------------


def test_create_rating_curve_transformation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds = DatastreamFactory(monitoring_site=monitoring_site)
    rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.post(
        _transformations_url(task.id),
        data=_rating_curve_body(output_ds, input_ds, rating_curve),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}

    detail = client.get(_detail_url(task.id, response.json()["id"]))
    body = detail.json()["data"]
    assert body["transformationType"] == "rating_curve"
    assert body["ratingCurveId"] == str(rating_curve.id)
    assert body["inputDatastreams"] == [
        {"datastreamId": str(input_ds.id), "variableName": None}
    ]


def test_create_derivation_transformation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds = DatastreamFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.post(
        _transformations_url(task.id),
        data=_derivation_body(output_ds, input_ds),
        content_type="application/json",
    )

    assert response.status_code == 201

    detail = client.get(_detail_url(task.id, response.json()["id"]))
    body = detail.json()["data"]
    assert body["transformationType"] == "derivation"
    assert body["formula"] == "x"
    assert body["inputDatastreams"] == [
        {"datastreamId": str(input_ds.id), "variableName": "x"}
    ]


def test_create_aggregation_transformation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds = DatastreamFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.post(
        _transformations_url(task.id),
        data=_aggregation_body(output_ds, input_ds),
        content_type="application/json",
    )

    assert response.status_code == 201

    detail = client.get(_detail_url(task.id, response.json()["id"]))
    body = detail.json()["data"]
    assert body["transformationType"] == "aggregation"
    assert body["aggregationMethod"] == "mean"
    assert body["outputInterval"] == 1


def test_create_transformation_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds = DatastreamFactory(monitoring_site=monitoring_site)
    rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)

    response = client.post(
        _transformations_url(task.id),
        data=_rating_curve_body(output_ds, input_ds, rating_curve),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_transformation_returns_403_without_edit_permission(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds = DatastreamFactory(monitoring_site=monitoring_site)
    rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        _transformations_url(task.id),
        data=_rating_curve_body(output_ds, input_ds, rating_curve),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_derivation_transformation_returns_400_when_formula_missing(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds = DatastreamFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.post(
        _transformations_url(task.id),
        data=_derivation_body(output_ds, input_ds, formula=None),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_aggregation_transformation_returns_400_when_rating_curve_set(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds = DatastreamFactory(monitoring_site=monitoring_site)
    rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.post(
        _transformations_url(task.id),
        data=_aggregation_body(output_ds, input_ds, ratingCurveId=str(rating_curve.id)),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_aggregation_transformation_returns_400_when_timezone_missing_for_iana(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    input_ds = DatastreamFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.post(
        _transformations_url(task.id),
        data=_aggregation_body(output_ds, input_ds, timezoneType="iana"),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_data_product_transformation ------------------------------------------------------


def test_get_transformation_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(_detail_url(task.id, transformation.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(transformation.id)


def test_get_transformation_returns_404_for_outsider(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(task.id, transformation.id))

    assert response.status_code == 404


def test_get_transformation_returns_404_for_nonexistent_transformation(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, _ = _make_task_with_monitoring_site(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(task.id, "00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_transformation_properties_rejects_unknown_property(client):
    """Single-item GET must validate `properties` the same way the list endpoint
    does -- regression test for the item-level validation gap this chunk closes."""
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(_detail_url(task.id, transformation.id), {"properties": "bogus"})

    assert response.status_code == 400


def test_get_transformation_included_is_present_but_empty_without_include_param(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(_detail_url(task.id, transformation.id))

    assert response.status_code == 200
    body = response.json()
    assert "included" in body
    assert body["included"] == {}


def test_get_transformation_include_rating_curve_sideloads_it(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(_detail_url(task.id, transformation.id), {"include": "ratingCurve"})

    assert response.status_code == 200
    body = response.json()
    assert [r["id"] for r in body["included"]["ratingCurves"]] == [
        str(transformation.rating_curve_id)
    ]


def test_get_transformation_include_rejects_unknown_relation(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.get(_detail_url(task.id, transformation.id), {"include": "bogus"})

    assert response.status_code == 400


# --- update_data_product_transformation ----------------------------------------------------


def test_update_transformation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    new_rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.patch(
        _detail_url(task.id, transformation.id),
        data={"ratingCurveId": str(new_rating_curve.id)},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(task.id, transformation.id))
    assert detail.json()["data"]["ratingCurveId"] == str(new_rating_curve.id)


def test_update_transformation_replaces_input_datastreams(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    new_input = DatastreamFactory(monitoring_site=monitoring_site)
    client.force_login(owner)

    response = client.patch(
        _detail_url(task.id, transformation.id),
        data={"inputDatastreams": [{"datastreamId": str(new_input.id)}]},
        content_type="application/json",
    )

    assert response.status_code == 204

    detail = client.get(_detail_url(task.id, transformation.id))
    assert detail.json()["data"]["inputDatastreams"] == [
        {"datastreamId": str(new_input.id), "variableName": None}
    ]


def test_update_transformation_rolls_back_input_datastreams_when_one_is_invalid(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    original_input = transformation.input_datastreams.get().datastream

    valid_input = DatastreamFactory(monitoring_site=monitoring_site)
    other_workspace_input = DatastreamFactory(monitoring_site=MonitoringSiteFactory())
    client.force_login(owner)

    response = client.patch(
        _detail_url(task.id, transformation.id),
        data={
            "inputDatastreams": [
                {"datastreamId": str(valid_input.id)},
                {"datastreamId": str(other_workspace_input.id)},
            ]
        },
        content_type="application/json",
    )

    assert response.status_code == 400

    detail = client.get(_detail_url(task.id, transformation.id))
    assert detail.json()["data"]["inputDatastreams"] == [
        {"datastreamId": str(original_input.id), "variableName": None}
    ]


def test_update_transformation_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    new_rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(task.id, transformation.id),
        data={"ratingCurveId": str(new_rating_curve.id)},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_data_product_transformation ------------------------------------------------------


def test_delete_transformation_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    client.force_login(owner)

    response = client.delete(_detail_url(task.id, transformation.id))

    assert response.status_code == 204
    assert client.get(_detail_url(task.id, transformation.id)).status_code == 404


def test_delete_transformation_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    task, monitoring_site = _make_task_with_monitoring_site(workspace)
    transformation = _make_rating_curve_transformation(task, monitoring_site)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(task.id, transformation.id))

    assert response.status_code == 403
