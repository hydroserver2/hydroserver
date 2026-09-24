from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from hydroserverpy.api.services.sta.datastream import DatastreamService
from hydroserverpy.api.utils import build_datetime_interval


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return dict(self._payload)


def make_service(*payloads):
    client = MagicMock()
    client.base_route = "/api/ogc"
    client.request.side_effect = [FakeResponse(payload) for payload in payloads]
    return DatastreamService(client), client


def sent_params(client, call=0):
    return client.request.call_args_list[call].kwargs["params"]


JAN_1 = datetime(2024, 1, 1, tzinfo=timezone.utc)


# --- build_datetime_interval ---------------------------------------------------------------


@pytest.mark.parametrize(
    "start, end, expected",
    [
        (..., ..., ...),
        (None, None, ...),
        (JAN_1, ..., "2024-01-01T00:00:00+00:00/.."),
        (..., JAN_1, "../2024-01-01T00:00:00+00:00"),
        (datetime(2024, 1, 1), None, "2024-01-01T00:00:00+00:00/.."),
        ("2024-01-01", "2024-02-01T00:00:00Z", "2024-01-01T00:00:00+00:00/2024-02-01T00:00:00+00:00"),
    ],
)
def test_build_datetime_interval(start, end, expected):
    assert build_datetime_interval(start, end) == expected


# --- DatastreamService.list -----------------------------------------------------------------


def test_list_sends_phenomenon_time_bounds_as_a_datetime_interval():
    service, client = make_service({"data": [], "meta": {"offset": 0, "limit": 100, "totalCount": 0}})

    service.list(phenomenon_time_min=JAN_1)

    params = sent_params(client)
    assert params["datetime"] == "2024-01-01T00:00:00+00:00/.."
    assert "phenomenon_time_min" not in params


def test_list_omits_datetime_without_bounds():
    service, client = make_service({"data": [], "meta": {"offset": 0, "limit": 100, "totalCount": 0}})

    service.list()

    assert "datetime" not in sent_params(client)


def test_list_keeps_the_phenomenon_time_bounds_when_paging():
    page = {"data": [], "meta": {"offset": 0, "limit": 100, "totalCount": 0}}
    service, client = make_service(page, page)

    collection = service.list(phenomenon_time_min=JAN_1, phenomenon_time_max=JAN_1)
    assert collection.filters["phenomenon_time_min"] == JAN_1
    assert "datetime" not in collection.filters

    collection.next_page()

    assert sent_params(client, 1)["datetime"] == sent_params(client, 0)["datetime"]
    assert sent_params(client, 1)["offset"] == 100


def test_list_fetch_all_keeps_the_phenomenon_time_bounds():
    full_page = {
        "data": [{"id": f"00000000-0000-0000-0000-00000000000{i}"} for i in range(2)],
        "meta": {"offset": 0, "limit": 2, "totalCount": 3},
    }
    last_page = {"data": [], "meta": {"offset": 2, "limit": 2, "totalCount": 3}}
    service, client = make_service(full_page, last_page)
    service.model = MagicMock()

    service.list(limit=2, phenomenon_time_min=JAN_1, fetch_all=True)

    assert client.request.call_count == 2
    assert sent_params(client, 1)["datetime"] == "2024-01-01T00:00:00+00:00/.."


# --- DatastreamService.get_observations -----------------------------------------------------


def test_get_observations_sends_a_datetime_interval_and_pages_with_the_same_bounds():
    columnar = {
        "data": {"phenomenonTime": [], "result": [], "resultQualifierCodes": []},
        "meta": {"offset": 0, "limit": 1, "totalCount": 0},
    }
    service, client = make_service(columnar, columnar)
    service.get = MagicMock()

    collection = service.get_observations(uid="ds-1", limit=1, phenomenon_time_min=JAN_1)
    assert collection.filters == {"phenomenon_time_min": JAN_1}

    service.get_observations(uid="ds-1", **collection.filters, offset=1, limit=1)

    assert sent_params(client, 0)["datetime"] == "2024-01-01T00:00:00+00:00/.."
    assert sent_params(client, 1)["datetime"] == "2024-01-01T00:00:00+00:00/.."
    assert "phenomenon_time_min" not in sent_params(client, 0)
