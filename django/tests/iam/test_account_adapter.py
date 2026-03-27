from smtplib import SMTPException

import pytest
from allauth.core.context import request_context
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from domains.iam.auth.adapters import AccountAdapter
from interfaces.account.navigation import (
    ACCOUNT_POST_AUTH_HANDOFF_SESSION_KEY,
    ACCOUNT_RETURN_TO_SESSION_KEY,
    get_post_auth_account_return_to,
)


class DummyMessage:
    def __init__(self, send_exception):
        self.send_exception = send_exception

    def send(self):
        raise self.send_exception


class DummyConnection:
    def __init__(self):
        self.messages = None

    def send_messages(self, messages):
        self.messages = messages
        return len(messages)


def attach_session(request):
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    return request


def test_account_adapter_falls_back_to_console_email_backend_in_dev(monkeypatch, settings):
    request = RequestFactory().get("/accounts/signup/")
    adapter = AccountAdapter()
    message = DummyMessage(ConnectionRefusedError(61, "Connection refused"))
    connection = DummyConnection()

    settings.DEPLOYMENT_BACKEND = "dev"
    monkeypatch.setattr(adapter, "render_mail", lambda *args, **kwargs: message)
    monkeypatch.setattr("domains.iam.auth.adapters.get_connection", lambda **kwargs: connection)

    with request_context(request):
        adapter.send_mail("account/email/email_confirmation", "user@example.com", {})

    assert connection.messages == [message]


def test_account_adapter_reraises_email_delivery_errors_outside_dev(
    monkeypatch, settings
):
    request = RequestFactory().get("/accounts/signup/")
    adapter = AccountAdapter()
    settings.DEPLOYMENT_BACKEND = "aws"
    monkeypatch.setattr(
        adapter,
        "render_mail",
        lambda *args, **kwargs: DummyMessage(SMTPException("smtp down")),
    )

    with request_context(request):
        with pytest.raises(SMTPException):
            adapter.send_mail("account/email/email_confirmation", "user@example.com", {})


def test_account_adapter_allows_registered_client_origins_as_return_urls(settings):
    adapter = AccountAdapter()

    settings.OIDC_BUNDLED_CLIENTS = {
        "test": {
            "id": "test-client",
            "redirect_uris": ["http://127.0.0.1:5173/callback"],
            "cors_origins": ["http://127.0.0.1:5173"],
        }
    }

    assert adapter.is_safe_url("http://127.0.0.1:5173/orchestration?workspaceId=123")
    assert not adapter.is_safe_url("http://malicious.example.com/orchestration")


def test_account_adapter_prefers_handoff_url_for_post_auth_redirects():
    request = attach_session(RequestFactory().get("/accounts/signup/"))
    request.user = type("AuthenticatedUser", (), {"is_authenticated": True})()
    request.session[ACCOUNT_RETURN_TO_SESSION_KEY] = "http://127.0.0.1:5173/sites"
    handoff_url = (
        "http://127.0.0.1:5173/auth/handoff"
        "?returnTo=http%3A%2F%2F127.0.0.1%3A5173%2Fsites"
    )
    request.session[ACCOUNT_POST_AUTH_HANDOFF_SESSION_KEY] = handoff_url
    adapter = AccountAdapter()

    with request_context(request):
        expected = handoff_url

        assert adapter.get_login_redirect_url(request) == expected
        assert adapter.get_signup_redirect_url(request) == expected
        assert adapter.get_email_verification_redirect_url(object()) == expected


def test_post_return_to_does_not_clear_stored_handoff():
    handoff_url = (
        "http://127.0.0.1:5173/auth/handoff"
        "?returnTo=http%3A%2F%2F127.0.0.1%3A5173%2Fsites"
    )
    request = attach_session(
        RequestFactory().post(
            "/accounts/signup/",
            {"next": "http://127.0.0.1:5173/sites"},
        )
    )
    request.session[ACCOUNT_RETURN_TO_SESSION_KEY] = "http://127.0.0.1:5173/sites"
    request.session[ACCOUNT_POST_AUTH_HANDOFF_SESSION_KEY] = handoff_url

    assert get_post_auth_account_return_to(request) == handoff_url
