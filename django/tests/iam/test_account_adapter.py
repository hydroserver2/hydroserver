from smtplib import SMTPException

import pytest
from allauth.core.context import request_context
from django.test import RequestFactory

from domains.iam.auth.adapters import AccountAdapter


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
