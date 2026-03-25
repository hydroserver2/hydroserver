import pytest
from allauth.idp.oidc.models import Client
from django.core.management import call_command


@pytest.fixture
def bundled_oidc_clients(settings):
    settings.OIDC_BUNDLED_CLIENTS = {
        "data-management": {
            "id": "hydroserver-data-management",
            "name": "HydroServer Data Management",
            "redirect_uris": [
                "https://data.example.com/callback",
                "https://preview.example.com/callback",
            ],
            "cors_origins": [
                "https://data.example.com",
                "https://preview.example.com",
            ],
        },
        "qc": {
            "id": "hydroserver-qc",
            "name": "HydroServer QC",
            "redirect_uris": ["https://qc.example.com/callback"],
            "cors_origins": ["https://qc.example.com"],
        },
    }
    return settings.OIDC_BUNDLED_CLIENTS


def test_register_oidc_clients_creates_bundled_clients(bundled_oidc_clients):
    call_command("register_oidc_clients")

    data_management_client = Client.objects.get(
        id=bundled_oidc_clients["data-management"]["id"]
    )
    qc_client = Client.objects.get(id=bundled_oidc_clients["qc"]["id"])

    assert Client.objects.count() == 2
    assert data_management_client.name == "HydroServer Data Management"
    assert data_management_client.type == Client.Type.PUBLIC
    assert data_management_client.get_scopes() == ["openid", "profile", "email"]
    assert data_management_client.get_default_scopes() == [
        "openid",
        "profile",
        "email",
    ]
    assert data_management_client.get_grant_types() == [
        Client.GrantType.AUTHORIZATION_CODE,
        Client.GrantType.REFRESH_TOKEN,
    ]
    assert data_management_client.get_response_types() == ["code"]
    assert data_management_client.get_redirect_uris() == bundled_oidc_clients[
        "data-management"
    ]["redirect_uris"]
    assert data_management_client.get_cors_origins() == bundled_oidc_clients[
        "data-management"
    ]["cors_origins"]
    assert data_management_client.skip_consent is True

    assert qc_client.name == "HydroServer QC"
    assert qc_client.type == Client.Type.PUBLIC
    assert qc_client.get_redirect_uris() == bundled_oidc_clients["qc"]["redirect_uris"]
    assert qc_client.get_cors_origins() == bundled_oidc_clients["qc"]["cors_origins"]
    assert qc_client.skip_consent is True


def test_register_oidc_clients_updates_existing_clients_without_rotating_secrets(
    bundled_oidc_clients,
):
    existing_client = Client.objects.create(
        id="hydroserver-data-management",
        name="Old Data App",
        secret="existing-secret",
        type=Client.Type.CONFIDENTIAL,
        scopes="openid",
        default_scopes="openid",
        grant_types=Client.GrantType.AUTHORIZATION_CODE,
        response_types="code",
        redirect_uris="https://old.example.com/callback",
        cors_origins="https://old.example.com",
        skip_consent=False,
    )

    call_command("register_oidc_clients")
    call_command("register_oidc_clients")

    existing_client.refresh_from_db()
    qc_client = Client.objects.get(id=bundled_oidc_clients["qc"]["id"])

    assert Client.objects.count() == 2
    assert existing_client.secret == "existing-secret"
    assert existing_client.name == "HydroServer Data Management"
    assert existing_client.type == Client.Type.PUBLIC
    assert existing_client.get_default_scopes() == ["openid", "profile", "email"]
    assert existing_client.get_grant_types() == [
        Client.GrantType.AUTHORIZATION_CODE,
        Client.GrantType.REFRESH_TOKEN,
    ]
    assert existing_client.get_redirect_uris() == bundled_oidc_clients[
        "data-management"
    ]["redirect_uris"]
    assert existing_client.get_cors_origins() == bundled_oidc_clients[
        "data-management"
    ]["cors_origins"]
    assert existing_client.skip_consent is True
    assert qc_client.type == Client.Type.PUBLIC
