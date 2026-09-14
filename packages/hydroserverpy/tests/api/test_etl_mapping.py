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


def test_create_mapping_refetches_after_created_response():
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

    assert str(mapping.uid) == mapping_id
    assert mapping.source_identifier == "sensor_1"
    assert str(mapping.target_datastream_id) == datastream_id
    assert mapping.task_id == task_id


def test_update_mapping_refetches_after_204():
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
                    "sourceIdentifier": "sensor_2",
                    "targetDatastreamId": datastream_id,
                }
            }
        ),
    ]

    service = EtlMappingService(client)
    mapping = service.update(task_id=task_id, uid=mapping_id, source_identifier="sensor_2")

    assert mapping.source_identifier == "sensor_2"
