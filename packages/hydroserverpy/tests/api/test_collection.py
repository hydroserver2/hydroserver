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


def _item(name):
    return {"id": str(uuid.uuid4()), "name": name}


def test_fetch_all_continues_past_an_underestimated_total_count():
    client = make_client()
    # Page 1 reports totalCount=2 (an estimate), but 5 items actually exist
    # across 3 pages of limit=2 - the last page is short, proving completion.
    client.request.side_effect = [
        FakeResponse({"data": [_item("a"), _item("b")], "meta": {"limit": 2, "offset": 0, "totalCount": 2}}),
        FakeResponse({"data": [_item("c"), _item("d")], "meta": {"limit": 2, "offset": 2, "totalCount": 2}}),
        FakeResponse({"data": [_item("e")], "meta": {"limit": 2, "offset": 4, "totalCount": 2}}),
    ]

    service = DummyService(client)
    first_page = service.list(limit=2)
    assert len(first_page.items) == 2

    result = first_page.fetch_all()

    assert [item.name for item in result.items] == ["a", "b", "c", "d", "e"]
    assert result.total_count == 5
    assert client.request.call_count == 3


def test_fetch_all_stops_immediately_when_first_page_is_already_short():
    client = make_client()
    client.request.side_effect = [
        FakeResponse({"data": [_item("a")], "meta": {"limit": 2, "offset": 0, "totalCount": 1}}),
    ]

    service = DummyService(client)
    first_page = service.list(limit=2)
    result = first_page.fetch_all()

    assert [item.name for item in result.items] == ["a"]
    assert result.total_count == 1
    assert client.request.call_count == 1
