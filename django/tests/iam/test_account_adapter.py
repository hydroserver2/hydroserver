from smtplib import SMTPException

import pytest
from allauth.core.context import request_context
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib import messages
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
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


def attach_messages(request):
    setattr(request, "_messages", FallbackStorage(request))
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


def test_account_adapter_clears_queued_messages_before_handoff_redirect():
    handoff_url = (
        "http://127.0.0.1:5173/auth/handoff"
        "?returnTo=http%3A%2F%2F127.0.0.1%3A5173%2Fsites"
    )
    request = attach_messages(attach_session(RequestFactory().get("/accounts/login/")))
    request.user = type("AuthenticatedUser", (), {"is_authenticated": True})()
    request.session[ACCOUNT_RETURN_TO_SESSION_KEY] = "http://127.0.0.1:5173/sites"
    request.session[ACCOUNT_POST_AUTH_HANDOFF_SESSION_KEY] = handoff_url
    messages.success(request, "Verify your email address.")
    adapter = AccountAdapter()

    with request_context(request):
        assert adapter.get_login_redirect_url(request) == handoff_url

    assert list(get_messages(request)) == []


def test_account_adapter_keeps_messages_for_non_handoff_redirects():
    redirect_url = "/accounts/profile/"
    request = attach_messages(attach_session(RequestFactory().get("/accounts/login/")))
    request.user = type("AuthenticatedUser", (), {"is_authenticated": True})()
    request.session[ACCOUNT_RETURN_TO_SESSION_KEY] = redirect_url
    messages.success(request, "Signed in successfully.")
    adapter = AccountAdapter()

    with request_context(request):
        assert adapter.get_login_redirect_url(request) == redirect_url

    queued_messages = list(get_messages(request))
    assert len(queued_messages) == 1
    assert str(queued_messages[0]) == "Signed in successfully."


def test_account_adapter_skips_logged_in_message_during_handoff(monkeypatch):
    request = attach_messages(attach_session(RequestFactory().get("/accounts/login/")))
    request.session[ACCOUNT_POST_AUTH_HANDOFF_SESSION_KEY] = (
        "http://127.0.0.1:5173/auth/handoff"
        "?returnTo=http%3A%2F%2F127.0.0.1%3A5173%2Fsites"
    )
    adapter = AccountAdapter()
    called = False

    def fake_add_message(self, request, level, **kwargs):
        nonlocal called
        called = True
        messages.add_message(request, level, kwargs.get("message") or "queued")

    monkeypatch.setattr(DefaultAccountAdapter, "add_message", fake_add_message)

    adapter.add_message(
        request,
        messages.SUCCESS,
        "account/messages/logged_in.txt",
        {"user": object()},
    )

    assert called is False
    assert list(get_messages(request)) == []


def test_account_adapter_keeps_non_redirect_message_during_handoff(monkeypatch):
    request = attach_messages(attach_session(RequestFactory().get("/accounts/login/")))
    request.session[ACCOUNT_POST_AUTH_HANDOFF_SESSION_KEY] = (
        "http://127.0.0.1:5173/auth/handoff"
        "?returnTo=http%3A%2F%2F127.0.0.1%3A5173%2Fsites"
    )
    adapter = AccountAdapter()
    called = False

    def fake_add_message(self, request, level, **kwargs):
        nonlocal called
        called = True
        messages.add_message(request, level, kwargs.get("message") or "queued")

    monkeypatch.setattr(DefaultAccountAdapter, "add_message", fake_add_message)

    adapter.add_message(
        request,
        messages.SUCCESS,
        "account/messages/login_code_sent.txt",
        {"recipient": "user@example.com"},
    )

    assert called is True
    queued_messages = list(get_messages(request))
    assert len(queued_messages) == 1
    assert str(queued_messages[0]) == "queued"
