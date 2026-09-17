import json
import uuid
from unittest.mock import MagicMock

from hydroserverpy.api.services.etl.mapping import EtlMappingService


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


def test_create_mapping_posts_to_flat_route_with_etl_task_id_in_body():
    client = make_client()
    task_id = uuid.uuid4()
    mapping_id = str(uuid.uuid4())
    datastream_id = str(uuid.uuid4())

    client.request.side_effect = [
        FakeResponse({"id": mapping_id}, status_code=201),
        FakeResponse(
            {
                "data": {
                    "id": mapping_id,
                    "etlTaskId": str(task_id),
                    "sourceIdentifier": "sensor_1",
                    "targetDatastreamId": datastream_id,
                }
            }
        ),
    ]

    service = EtlMappingService(client)
    mapping = service.create(
        task_id=task_id, source_identifier="sensor_1", target_datastream=datastream_id
    )

    post_call = client.request.call_args_list[0]
    assert post_call.args[0] == "post"
    assert post_call.args[1] == "//api/data/etl-mappings"
    sent_body = json.loads(post_call.kwargs["data"])
    assert sent_body["etlTaskId"] == str(task_id)

    get_call = client.request.call_args_list[1]
    assert get_call.args[1] == f"//api/data/etl-mappings/{mapping_id}"

    assert str(mapping.uid) == mapping_id
    assert mapping.source_identifier == "sensor_1"
    assert str(mapping.target_datastream_id) == datastream_id
    assert mapping.task_id == task_id


def test_update_mapping_patches_flat_route_and_refetches_after_204():
    client = make_client()
    task_id = uuid.uuid4()
    mapping_id = str(uuid.uuid4())
    datastream_id = str(uuid.uuid4())

    client.request.side_effect = [
        FakeResponse(None, status_code=204),
        FakeResponse(
            {
                "data": {
                    "id": mapping_id,
                    "etlTaskId": str(task_id),
                    "sourceIdentifier": "sensor_2",
                    "targetDatastreamId": datastream_id,
                }
            }
        ),
    ]

    service = EtlMappingService(client)
    mapping = service.update(uid=mapping_id, source_identifier="sensor_2")

    patch_call = client.request.call_args_list[0]
    assert patch_call.args[0] == "patch"
    assert patch_call.args[1] == f"//api/data/etl-mappings/{mapping_id}"
    sent_body = json.loads(patch_call.kwargs["data"])
    assert sent_body == {"sourceIdentifier": "sensor_2"}

    assert mapping.source_identifier == "sensor_2"
