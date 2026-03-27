from io import StringIO

from allauth.socialaccount.models import SocialApp
from django.core.management import call_command

from interfaces.web.views import _social_app_is_visible


def test_setup_local_google_socialapp_hides_placeholder_provider():
    SocialApp.objects.filter(provider="google").delete()
    stdout = StringIO()

    call_command(
        "setup_local_google_socialapp",
        client_id="",
        secret="",
        stdout=stdout,
    )

    social_app = SocialApp.objects.get(provider="google")

    assert social_app.client_id == "local-google-preview.apps.googleusercontent.com"
    assert social_app.settings["preview_only"] is True
    assert social_app.settings["hidden"] is True
    assert not _social_app_is_visible(social_app)
    assert "hidden locally to avoid invalid_client errors" in stdout.getvalue()


def test_setup_local_google_socialapp_uses_real_credentials_when_supplied():
    SocialApp.objects.filter(provider="google").delete()

    call_command(
        "setup_local_google_socialapp",
        client_id="real-client-id.apps.googleusercontent.com",
        secret="real-client-secret",
    )

    social_app = SocialApp.objects.get(provider="google")

    assert social_app.client_id == "real-client-id.apps.googleusercontent.com"
    assert social_app.secret == "real-client-secret"
    assert social_app.settings["preview_only"] is False
    assert social_app.settings["hidden"] is False
    assert _social_app_is_visible(social_app)


def test_setup_local_google_socialapp_preserves_existing_real_credentials():
    social_app = SocialApp.objects.create(
        provider="google",
        provider_id="google",
        name="Google",
        client_id="existing-client-id.apps.googleusercontent.com",
        secret="existing-client-secret",
        settings={"preview_only": False, "hidden": False},
    )

    call_command(
        "setup_local_google_socialapp",
        client_id="",
        secret="",
    )

    social_app.refresh_from_db()

    assert social_app.client_id == "existing-client-id.apps.googleusercontent.com"
    assert social_app.secret == "existing-client-secret"
    assert social_app.settings["preview_only"] is False
    assert social_app.settings["hidden"] is False
