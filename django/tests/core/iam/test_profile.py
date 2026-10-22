import pytest
from django.urls import reverse

from core.iam.models import User


pytestmark = pytest.mark.django_db


@pytest.fixture
def profile_user(client):
    user = User.objects.create_user(
        email="profile@example.test",
        password="password",
        first_name="Jane",
        middle_name="Ann",
        last_name="Doe",
        phone="+18015551234",
        address="123 Main Street",
        link="https://example.com/jane",
        user_type="Other",
    )
    client.force_login(user)
    return user


def test_profile_edit_renders_existing_contact_fields(client, profile_user):
    response = client.get(reverse("account_profile_edit"))

    assert response.status_code == 200
    for name in ("middle_name", "phone", "address", "link"):
        assert f'name="{name}"'.encode() in response.content
        assert f'value="{getattr(profile_user, name)}"'.encode() in response.content
        assert not response.context["form"].fields[name].required


@pytest.mark.parametrize("clear", [False, True])
def test_profile_edit_saves_and_displays_contact_fields(client, profile_user, clear):
    contact_data = {
        "middle_name": "Beth",
        "phone": "+18015559876",
        "address": "456 River Road",
        "link": "https://example.com/updated",
    }
    if clear:
        contact_data = {name: "" for name in contact_data}

    response = client.post(
        reverse("account_profile_edit"),
        {"first_name": "Jane", "last_name": "Doe", "user_type": "Other", **contact_data},
        follow=True,
    )

    assert response.redirect_chain == [(reverse("account_profile"), 302)]
    profile_user.refresh_from_db()
    for name, value in contact_data.items():
        assert (getattr(profile_user, name) or "") == value
        if value:
            assert value.encode() in response.content


def test_profile_edit_rejects_invalid_link_and_preserves_input(client, profile_user):
    response = client.post(
        reverse("account_profile_edit"),
        {
            "first_name": "Jane",
            "last_name": "Doe",
            "middle_name": "Beth",
            "phone": "+18015559876",
            "address": "456 River Road",
            "link": "not a URL",
            "user_type": "Other",
        },
    )

    assert response.status_code == 200
    assert response.context["form"].errors.get("link")
    assert b'value="Beth"' in response.content
    assert b'value="not a URL"' in response.content
    profile_user.refresh_from_db()
    assert profile_user.link == "https://example.com/jane"
