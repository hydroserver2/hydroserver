import uuid
from unittest.mock import MagicMock

from hydroserverpy.api.models.base import HydroServerBaseModel
from hydroserverpy.api.services.base import HydroServerBaseService


class DummyModel(HydroServerBaseModel):
    name: str

    @classmethod
    def get_route(cls):
        return "dummy"


class DummyService(HydroServerBaseService):
    def __init__(self, client):
        self.model = DummyModel
        super().__init__(client)


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


def test_get_unwraps_item_envelope():
    client = make_client()
    item_id = str(uuid.uuid4())
    client.request.return_value = FakeResponse({"data": {"id": item_id, "name": "Foo"}, "included": {}})

    service = DummyService(client)
    result = service.get(item_id)

    assert isinstance(result, DummyModel)
    assert str(result.uid) == item_id
    assert result.name == "Foo"


def test_create_from_id_only_response_refetches_canonical_state():
    client = make_client()
    item_id = str(uuid.uuid4())
    # Create returns only {"id": ...}; the base service should follow up with a GET.
    client.request.side_effect = [
        FakeResponse({"id": item_id}, status_code=201),
        FakeResponse({"data": {"id": item_id, "name": "Foo"}}),
    ]

    service = DummyService(client)
    result = service.create(name="Foo")

    assert isinstance(result, DummyModel)
    assert str(result.uid) == item_id
    assert result.name == "Foo"
    assert client.request.call_count == 2


def test_create_from_full_bare_object_response_still_works():
    client = make_client()
    item_id = str(uuid.uuid4())
    # A handful of legacy endpoints return the full resource instead of {"id": ...}.
    client.request.side_effect = [
        FakeResponse({"id": item_id, "name": "Foo"}, status_code=201),
        FakeResponse({"data": {"id": item_id, "name": "Foo"}}),
    ]

    service = DummyService(client)
    result = service.create(name="Foo")

    assert isinstance(result, DummyModel)
    assert str(result.uid) == item_id
    assert result.name == "Foo"


def test_update_refetches_after_204_no_content():
    client = make_client()
    item_id = str(uuid.uuid4())
    client.request.side_effect = [
        FakeResponse(None, status_code=204),
        FakeResponse({"data": {"id": item_id, "name": "Updated"}}),
    ]

    service = DummyService(client)
    result = service.update(item_id, name="Updated")

    assert isinstance(result, DummyModel)
    assert result.name == "Updated"
    assert client.request.call_count == 2


def test_update_refetches_even_when_patch_returns_full_body():
    client = make_client()
    item_id = str(uuid.uuid4())
    client.request.side_effect = [
        FakeResponse({"id": item_id, "name": "Updated"}, status_code=200),
        FakeResponse({"data": {"id": item_id, "name": "Updated"}}),
    ]

    service = DummyService(client)
    result = service.update(item_id, name="Updated")

    assert isinstance(result, DummyModel)
    assert result.name == "Updated"
