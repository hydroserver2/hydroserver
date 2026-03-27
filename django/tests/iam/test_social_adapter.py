from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from domains.iam.auth.adapters import SocialAccountAdapter


User = get_user_model()


def _build_request():
    request = RequestFactory().get("/")
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    return request


def test_social_save_user_without_form_sets_defaults(settings):
    request = _build_request()
    user = User(email="social-new@example.com")
    social_account = SocialAccount(
        provider="google",
        uid="google-uid-123",
        extra_data={
            "given_name": "Jane",
            "family_name": "Doe",
            "email": "social-new@example.com",
        },
    )
    sociallogin = SocialLogin(user=user, account=social_account)

    adapter = SocialAccountAdapter()
    saved_user = adapter.save_user(request, sociallogin, form=None)

    assert saved_user.first_name == "Jane"
    assert saved_user.last_name == "Doe"
    assert saved_user.user_type == "Unspecified"
    assert saved_user.is_ownership_allowed == settings.ACCOUNT_OWNERSHIP_ENABLED
    assert not saved_user.has_usable_password()
    assert saved_user.pk is not None


def test_social_save_user_without_form_handles_missing_extra_data(settings):
    request = _build_request()
    user = User(email="social-minimal@example.com")
    social_account = SocialAccount(
        provider="orcid",
        uid="orcid-uid-456",
        extra_data={},
    )
    sociallogin = SocialLogin(user=user, account=social_account)

    adapter = SocialAccountAdapter()
    saved_user = adapter.save_user(request, sociallogin, form=None)

    assert saved_user.user_type == "Unspecified"
    assert saved_user.is_ownership_allowed == settings.ACCOUNT_OWNERSHIP_ENABLED
    assert saved_user.pk is not None
