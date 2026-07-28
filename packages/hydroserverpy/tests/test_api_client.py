import pytest
import requests

from hydroserverpy.api import client as client_module


class FakeResponse:
    def __init__(self, status_code=200, content=b"{}"):
        self.status_code = status_code
        self.content = content

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

    response = hs.request("get", "/api/data/workspaces")

    assert response is second_response
    assert fake_session_factory[0].closed is True
    assert hs._session is replacement_session
    assert hs._session.auth == ("user@example.com", "secret")
