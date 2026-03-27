from types import MethodType
from uuid import uuid4

import pytest
from allauth.account.forms import SignupForm
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import get_adapter as get_socialaccount_adapter
from allauth.socialaccount.models import SocialAccount, SocialLogin
from allauth.headless.socialaccount.inputs import SignupInput
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse

from interfaces.account.forms import ProfileForm
from domains.iam.models import Organization, OrganizationType, UserType


User = get_user_model()


@pytest.fixture(autouse=True)
def ensure_account_vocabulary():
    UserType.objects.get_or_create(name="Other", defaults={"public": True})
    OrganizationType.objects.get_or_create(name="Other", defaults={"public": True})


def signup_payload(email: str):
    return {
        "email": email,
        "password1": "HydroServer123!",
        "password2": "HydroServer123!",
        "firstName": "New",
        "middleName": "Flow",
        "lastName": "User",
        "phone": "4355550100",
        "address": "123 Test Street",
        "link": "https://example.com/profile",
        "type": "Other",
        "organization": {
            "code": "ORG",
            "name": "Test Organization",
            "description": "Organization captured during signup.",
            "link": "https://example.com/org",
            "type": "Other",
        },
    }


def flat_signup_payload(email: str):
    return {
        "email": email,
        "password1": "HydroServer123!",
        "password2": "HydroServer123!",
        "firstName": "New",
        "middleName": "Flow",
        "lastName": "User",
        "phone": "4355550100",
        "address": "123 Test Street",
        "link": "https://example.com/profile",
        "type": "Other",
        "has_organization": "on",
        "org_name": "Test Organization",
        "org_code": "ORG",
        "org_description": "Organization captured during signup.",
        "org_link": "https://example.com/org",
        "org_type": "Other",
    }


def assert_extended_profile(user):
    user.refresh_from_db()
    assert user.first_name == "New"
    assert user.middle_name == "Flow"
    assert user.last_name == "User"
    assert user.phone == "4355550100"
    assert user.address == "123 Test Street"
    assert user.link == "https://example.com/profile"
    assert user.user_type == "Other"
    assert user.organization is not None
    assert user.organization.code == "ORG"
    assert user.organization.name == "Test Organization"
    assert user.organization.description == "Organization captured during signup."
    assert user.organization.link == "https://example.com/org"
    assert user.organization.organization_type == "Other"


def test_account_signup_saves_extended_profile_fields(settings):
    request = build_request("/accounts/signup/")
    email = f"signup-{uuid4().hex}@example.com"
    form = SignupForm(data=signup_payload(email))

    assert form.is_valid(), form.errors

    user = form.save(request)

    assert user.email == email
    assert user.is_ownership_allowed == settings.ACCOUNT_OWNERSHIP_ENABLED
    assert_extended_profile(user)


def test_account_signup_saves_flat_organization_fields(settings):
    request = build_request("/accounts/signup/")
    email = f"signup-flat-{uuid4().hex}@example.com"
    form = SignupForm(data=flat_signup_payload(email))

    assert form.is_valid(), form.errors

    user = form.save(request)

    assert user.email == email
    assert user.is_ownership_allowed == settings.ACCOUNT_OWNERSHIP_ENABLED
    assert_extended_profile(user)


def test_oidc_signup_saves_extended_profile_fields():
    request = build_request("/api/auth/app/provider/signup")
    email = f"oidc-{uuid4().hex}@example.com"
    form = SignupInput(data=signup_payload(email), sociallogin=build_sociallogin(email))

    assert {"first_name", "middle_name", "last_name", "phone", "address", "link", "user_type", "organization"} <= set(form.fields)
    assert form.is_valid(), form.errors

    sociallogin = form.sociallogin
    user = get_socialaccount_adapter().save_user(request, sociallogin, form=form)

    assert user.email == email
    assert_extended_profile(user)


def test_profile_form_saves_extended_profile_fields(get_principal):
    user = get_principal("owner")
    form = ProfileForm(
        data={
            "first_name": "Edited",
            "middle_name": "Profile",
            "last_name": "Owner",
            "phone": "4355550111",
            "address": "500 Updated Street",
            "link": "https://example.com/edited",
            "user_type": "Other",
            "has_organization": "on",
            "org_name": "Edited Organization",
            "org_code": "EDIT",
            "org_description": "Updated from the profile form.",
            "org_link": "https://example.com/edited-org",
            "org_type": "Other",
        },
        instance=user,
    )

    assert form.is_valid(), form.errors

    updated_user = form.save()
    updated_user.refresh_from_db()

    assert updated_user.first_name == "Edited"
    assert updated_user.middle_name == "Profile"
    assert updated_user.last_name == "Owner"
    assert updated_user.phone == "4355550111"
    assert updated_user.address == "500 Updated Street"
    assert updated_user.link == "https://example.com/edited"
    assert updated_user.user_type == "Other"
    assert updated_user.organization is not None
    assert updated_user.organization.code == "EDIT"
    assert updated_user.organization.name == "Edited Organization"
    assert updated_user.organization.description == "Updated from the profile form."
    assert updated_user.organization.link == "https://example.com/edited-org"
    assert updated_user.organization.organization_type == "Other"


def test_profile_form_can_remove_organization(get_principal):
    user = get_principal("owner")
    user.organization = Organization.objects.create(
        code="REMOVE",
        name="Remove Me",
        organization_type="Other",
    )
    user.save()

    form = ProfileForm(
        data={
            "first_name": user.first_name,
            "middle_name": user.middle_name or "",
            "last_name": user.last_name,
            "phone": user.phone or "",
            "address": user.address or "",
            "link": user.link or "",
            "user_type": user.user_type,
        },
        instance=user,
    )

    assert form.is_valid(), form.errors

    updated_user = form.save()
    updated_user.refresh_from_db()

    assert updated_user.organization is None


def test_signup_page_marks_required_fields(client):
    response = client.get(reverse("account_signup"))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'First name<span class="text-red-600"> *</span>' in content
    assert 'Last name<span class="text-red-600"> *</span>' in content
    assert 'Email<span class="text-red-600"> *</span>' in content
    assert 'Password<span class="text-red-600"> *</span>' in content
    assert 'Confirm password<span class="text-red-600"> *</span>' in content
    assert 'User type<span class="text-red-600"> *</span>' in content


def test_email_verification_sent_page_renders():
    request = RequestFactory().get("/accounts/confirm-email/")
    content = render_to_string("account/verification_sent.html", request=request)

    assert "Verify your email" in content


def test_account_signup_requires_first_name():
    payload = signup_payload(f"signup-missing-first-{uuid4().hex}@example.com")
    payload["firstName"] = ""
    form = SignupForm(data=payload)

    assert not form.is_valid()
    assert "first_name" in form.errors


def test_account_signup_requires_last_name():
    payload = signup_payload(f"signup-missing-last-{uuid4().hex}@example.com")
    payload["lastName"] = ""
    form = SignupForm(data=payload)

    assert not form.is_valid()
    assert "last_name" in form.errors


def test_account_signup_invalid_post_rerenders_without_jsonfield_type_error(client):
    response = client.post(
        reverse("account_signup"),
        {
            "email": f"signup-browser-{uuid4().hex}@example.com",
            "password1": "HydroServer123!",
            "password2": "HydroServer123!",
            "first_name": "",
            "middle_name": "",
            "last_name": "User",
            "phone": "",
            "address": "",
            "link": "",
            "user_type": "Other",
            "organization": "",
        },
    )

    assert response.status_code == 200
    assert b"This field is required." in response.content


@pytest.fixture
def social_only_user():
    user = User.objects.create_user(
        email="social@example.com",
        password=None,
        first_name="Social",
        last_name="User",
        user_type="Other",
    )
    user.set_unusable_password()
    user.save()
    EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
    return user


def test_profile_edit_works_for_social_only_user(client, social_only_user):
    client.force_login(social_only_user)

    response = client.post(
        reverse("account_profile_edit"),
        {
            "first_name": "Updated",
            "middle_name": "",
            "last_name": "User",
            "phone": "",
            "address": "",
            "link": "",
            "user_type": "Other",
        },
    )

    assert response.status_code == 302
    social_only_user.refresh_from_db()
    assert social_only_user.first_name == "Updated"


def test_delete_account_works_for_social_only_user(client, social_only_user):
    client.force_login(social_only_user)

    response = client.post(
        reverse("account_delete"),
        {"confirmation": "delete my account and data"},
    )

    assert response.status_code == 302
    assert not User.objects.filter(email="social@example.com").exists()


def build_sociallogin(email: str):
    sociallogin = SocialLogin(
        user=User(email=email, username=email),
        account=SocialAccount(provider="openid_connect", uid=f"oidc-{uuid4().hex}"),
    )

    sociallogin.save = MethodType(lambda self, request: None, sociallogin)
    return sociallogin


def build_request(path: str):
    request = RequestFactory().post(path)
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    return request
