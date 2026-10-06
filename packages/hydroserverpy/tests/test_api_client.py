import json

import pytest
import requests

from hydroserverpy.api import client as client_module


class FakeResponse:
    def __init__(self, status_code=200, content=b"{}"):
        self.status_code = status_code
        self.content = content

    def json(self):
        return json.loads(self.content)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.auth = None
        self.closed = False
        self._responses = {"get": [], "post": [], "patch": [], "delete": []}

    def queue(self, method, *responses):
        self._responses[method].extend(responses)

    def close(self):
        self.closed = True

    def _request(self, method, *args, **kwargs):
        self.last_kwargs = kwargs
        response = self._responses[method].pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def get(self, *args, **kwargs):
        return self._request("get", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._request("post", *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self._request("patch", *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._request("delete", *args, **kwargs)


@pytest.fixture
def fake_session_factory(monkeypatch):
    sessions = []

    def factory():
        session = FakeSession()
        sessions.append(session)
        return session

    monkeypatch.setattr(client_module.requests, "Session", factory)
    return sessions


def test_hydroserver_uses_basic_auth_for_email_password(fake_session_factory):
    hs = client_module.HydroServer(
        host="https://example.com",
        email="user@example.com",
        password="secret",
    )

    assert hs._session is fake_session_factory[0]
    assert hs._session.auth == ("user@example.com", "secret")
    assert "X-API-Key" not in hs._session.headers


def test_hydroserver_uses_api_key_header(fake_session_factory):
    hs = client_module.HydroServer(
        host="https://example.com",
        apikey="hs_test_api_key",
    )

    assert hs._session is fake_session_factory[0]
    assert hs._session.auth is None
    assert hs._session.headers["X-API-Key"] == "hs_test_api_key"


def test_hydroserver_requires_both_email_and_password(fake_session_factory):
    with pytest.raises(ValueError, match="Both email and password"):
        client_module.HydroServer(
            host="https://example.com",
            email="user@example.com",
        )


def test_hydroserver_retries_connection_errors_with_same_basic_auth(
    fake_session_factory, monkeypatch
):
    first_response = requests.exceptions.ConnectionError("network issue")
    second_response = FakeResponse()

    hs = client_module.HydroServer(
        host="https://example.com",
        email="user@example.com",
        password="secret",
    )
    fake_session_factory[0].queue("get", first_response)

    replacement_session = FakeSession()
    replacement_session.auth = ("user@example.com", "secret")
    replacement_session.queue("get", second_response)

    def next_session():
        if len(fake_session_factory) == 1:
            fake_session_factory.append(replacement_session)
            return replacement_session
        return replacement_session

    monkeypatch.setattr(client_module.requests, "Session", next_session)

    response = hs.request("get", "/api/ogc/collections/workspaces/items")

    assert response is second_response
    assert fake_session_factory[0].closed is True
    assert hs._session is replacement_session
    assert hs._session.auth == ("user@example.com", "secret")


def test_hydroserver_encodes_boolean_query_params_in_lowercase(fake_session_factory):
    hs = client_module.HydroServer(host="https://example.com", apikey="hs_test_api_key")
    fake_session_factory[0].queue("get", FakeResponse())

    hs.request(
        "get",
        "/api/ogc/collections/workspaces/items",
        params={"isPrivate": True, "isAssociated": False, "workspaceId": ["a", "null"], "limit": 5},
    )

    assert fake_session_factory[0].last_kwargs["params"] == {
        "isPrivate": "true",
        "isAssociated": "false",
        "workspaceId": ["a", "null"],
        "limit": 5,
    }


def test_workspace_list_sends_lowercase_booleans(fake_session_factory):
    hs = client_module.HydroServer(host="https://example.com", apikey="hs_test_api_key")
    fake_session_factory[0].queue(
        "get", FakeResponse(content=b'{"data": [], "meta": {"limit": 100, "offset": 0, "totalCount": 0}}')
    )

    hs.workspaces.list(is_private=True, is_associated=False)

    url = requests.Request(
        "GET", "https://example.com", params=fake_session_factory[0].last_kwargs["params"]
    ).prepare().url
    assert "isPrivate=true" in url
    assert "isAssociated=false" in url


RUN_ID = "01a0e94d-307f-7347-8f40-66fb0327d09e"
RUN_RESPONSE = json.dumps(
    {"data": {"id": RUN_ID, "status": "PENDING"}, "included": None, "links": []}
).encode()


@pytest.mark.parametrize("service", ["etltasks", "monitoringtasks", "dataproducttasks"])
def test_task_trigger_and_get_run_unwrap_the_item_envelope(fake_session_factory, service):
    hs = client_module.HydroServer(host="https://example.com", apikey="hs_test_api_key")
    fake_session_factory[0].queue("post", FakeResponse(status_code=202, content=RUN_RESPONSE))
    fake_session_factory[0].queue("get", FakeResponse(content=RUN_RESPONSE))

    triggered = getattr(hs, service).trigger("task-1")
    fetched = getattr(hs, service).get_run("task-1", RUN_ID)

    assert str(triggered.id) == RUN_ID
    assert triggered.status == "PENDING"
    assert str(fetched.id) == RUN_ID


def test_list_sends_camel_case_params_and_keeps_public_filter_names(fake_session_factory):
    hs = client_module.HydroServer(host="https://example.com", apikey="hs_test_api_key")
    fake_session_factory[0].queue(
        "get", FakeResponse(content=b'{"data": [], "meta": {"limit": 100, "offset": 0, "totalCount": 0}}')
    )

    collection = hs.datastreams.list(
        workspace="00000000-0000-0000-0000-000000000001", is_private=False, tag=("river", "green")
    )

    params = fake_session_factory[0].last_kwargs["params"]
    assert params["workspaceId"] == "00000000-0000-0000-0000-000000000001"
    assert params["isPrivate"] == "false"
    assert params["tag"] == ["river:green"]
    assert not any("_" in key for key in params)
    assert collection.filters["workspace"] == "00000000-0000-0000-0000-000000000001"
    assert collection.filters["tag"] == ("river", "green")
