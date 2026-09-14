import uuid
from unittest.mock import MagicMock

from hydroserverpy.api.services.products.transformation import DataProductTransformationService


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        if self._payload is None:
            raise ValueError("No JSON content (empty response body)")
        return self._payload


def make_client():
    client = MagicMock()
    client.base_route = "/api/data"
    return client


def test_create_rating_curve_posts_to_unified_route_with_input_datastreams_list():
    client = make_client()
    task_id = uuid.uuid4()
    transformation_id = str(uuid.uuid4())
    output_id = str(uuid.uuid4())
    input_id = str(uuid.uuid4())
    rating_curve_id = str(uuid.uuid4())

    client.request.side_effect = [
        FakeResponse({"id": transformation_id}, status_code=201),
        FakeResponse(
            {
                "data": {
                    "id": transformation_id,
                    "transformationType": "rating_curve",
                    "outputDatastreamId": output_id,
                    "inputDatastreams": [{"datastreamId": input_id, "variableName": None}],
                    "ratingCurveId": rating_curve_id,
                }
            }
        ),
    ]

    service = DataProductTransformationService(client)
    transformation = service.create_rating_curve(
        task_id=task_id,
        output_datastream=output_id,
        input_datastream=input_id,
        rating_curve=rating_curve_id,
    )

    post_call = client.request.call_args_list[0]
    assert post_call.args[0] == "post"
    assert post_call.args[1] == f"//api/data/products/tasks/{task_id}/transformations"

    assert str(transformation.id) == transformation_id
    assert str(transformation.input_datastream_id) == input_id
    assert str(transformation.rating_curve_id) == rating_curve_id


def test_get_rating_curve_hits_the_unified_detail_route_not_a_type_slug():
    client = make_client()
    task_id = uuid.uuid4()
    transformation_id = str(uuid.uuid4())

    client.request.return_value = FakeResponse(
        {
            "data": {
                "id": transformation_id,
                "transformationType": "rating_curve",
                "outputDatastreamId": str(uuid.uuid4()),
                "inputDatastreams": [{"datastreamId": str(uuid.uuid4())}],
                "ratingCurveId": str(uuid.uuid4()),
            }
        }
    )

    service = DataProductTransformationService(client)
    service.get_rating_curve(task_id=task_id, uid=transformation_id)

    args, _ = client.request.call_args
    assert args[1] == f"//api/data/products/tasks/{task_id}/transformations/{transformation_id}"


def test_list_derivation_filters_by_transformation_type_on_the_unified_route():
    client = make_client()
    task_id = uuid.uuid4()

    client.request.return_value = FakeResponse({"data": []})

    service = DataProductTransformationService(client)
    service.list_derivation(task_id=task_id)

    args, kwargs = client.request.call_args
    assert args[1] == f"//api/data/products/tasks/{task_id}/transformations"
    assert kwargs["params"]["transformation_type"] == "derivation"


def test_update_aggregation_patches_then_refetches_by_id():
    client = make_client()
    task_id = uuid.uuid4()
    transformation_id = str(uuid.uuid4())
    input_id = str(uuid.uuid4())

    client.request.side_effect = [
        FakeResponse(None, status_code=204),
        FakeResponse(
            {
                "data": {
                    "id": transformation_id,
                    "transformationType": "aggregation",
                    "outputDatastreamId": str(uuid.uuid4()),
                    "inputDatastreams": [{"datastreamId": input_id}],
                    "aggregationMethod": "mean",
                    "outputInterval": 15,
                    "outputIntervalUnits": "minutes",
                }
            }
        ),
    ]

    service = DataProductTransformationService(client)
    transformation = service.update_aggregation(
        task_id=task_id,
        uid=transformation_id,
        input_datastream=input_id,
        aggregation_method="mean",
        output_interval=15,
        output_interval_units="minutes",
    )

    patch_call = client.request.call_args_list[0]
    assert patch_call.args[0] == "patch"
    assert patch_call.args[1] == f"//api/data/products/tasks/{task_id}/transformations/{transformation_id}"
    assert str(transformation.input_datastream_id) == input_id
