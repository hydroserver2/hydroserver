import uuid
from unittest.mock import MagicMock

import pytest

from hydroserverpy.api.services.sta.datastream import DatastreamService
from hydroserverpy.api.services.sta.monitoring_site import MonitoringSiteService


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
    client.base_route = "/api/ogc"
    return client


def linked_resource_payload(linked_resource_id, name="Report A"):
    return {
        "id": str(linked_resource_id),
        "name": name,
        "description": None,
        "type": "Report",
        "link": f"https://example.com/{name}",
    }


@pytest.fixture(params=[DatastreamService, MonitoringSiteService])
def service(request):
    return request.param(make_client())


def test_get_linked_resources_unwraps_data_and_forwards_params(service):
    parent_id = uuid.uuid4()
    items = [linked_resource_payload(uuid.uuid4())]
    service.client.request.return_value = FakeResponse(
        {"data": items, "meta": {"limit": 10, "offset": 20, "numberMatched": 21}, "links": []}
    )

    result = service.get_linked_resources(parent_id, offset=20, limit=10, type=["Report"])

    assert result == items
    method, path = service.client.request.call_args.args
    assert method == "get"
    assert path.endswith(f"/{parent_id}/linked-resources")
    assert service.client.request.call_args.kwargs["params"] == {
        "offset": 20,
        "limit": 10,
        "type": ["Report"],
    }


def test_get_linked_resources_omits_unset_params(service):
    service.client.request.return_value = FakeResponse({"data": [], "meta": {}, "links": []})

    service.get_linked_resources(uuid.uuid4())

    assert service.client.request.call_args.kwargs["params"] == {}


def test_get_linked_resource_unwraps_data(service):
    parent_id = uuid.uuid4()
    linked_resource_id = uuid.uuid4()
    item = linked_resource_payload(linked_resource_id)
    service.client.request.return_value = FakeResponse({"data": item, "links": []})

    result = service.get_linked_resource(parent_id, linked_resource_id)

    assert result == item
    service.client.request.assert_called_once()
    method, path = service.client.request.call_args.args
    assert method == "get"
    assert path.endswith(f"/{parent_id}/linked-resources/{linked_resource_id}")


def test_add_linked_resource_returns_created_item(service):
    parent_id = uuid.uuid4()
    linked_resource_id = uuid.uuid4()
    item = linked_resource_payload(linked_resource_id)
    service.client.request.side_effect = [
        FakeResponse({"id": str(linked_resource_id)}, status_code=201),
        FakeResponse({"data": item, "links": []}),
    ]

    result = service.add_linked_resource(
        parent_id, name="Report A", type="Report", url="https://example.com/Report A"
    )

    assert result == item
    method, path = service.client.request.call_args.args
    assert method == "get"
    assert path.endswith(f"/{parent_id}/linked-resources/{linked_resource_id}")


def test_update_linked_resource_returns_updated_item(service):
    parent_id = uuid.uuid4()
    linked_resource_id = uuid.uuid4()
    item = linked_resource_payload(linked_resource_id, name="Renamed")
    service.client.request.side_effect = [
        FakeResponse(status_code=204),
        FakeResponse({"data": item, "links": []}),
    ]

    result = service.update_linked_resource(parent_id, linked_resource_id, name="Renamed")

    assert result == item
    method, path = service.client.request.call_args.args
    assert method == "get"
    assert path.endswith(f"/{parent_id}/linked-resources/{linked_resource_id}")
