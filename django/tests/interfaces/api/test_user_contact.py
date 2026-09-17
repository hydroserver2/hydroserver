import pytest

from interfaces.api.schemas.iam.user import UserContactResponse
from tests.core.iam.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_user_contact_response_serializes_expected_fields_by_alias():
    user = UserFactory(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        user_type="Researcher",
        phone="555-0100",
        address="123 Analytical Engine Way",
        link="https://example.com/ada",
    )

    response = UserContactResponse.model_validate(user)
    data = response.model_dump(by_alias=True)

    assert data == {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "organizationName": None,
        "phone": "555-0100",
        "address": "123 Analytical Engine Way",
        "link": "https://example.com/ada",
        "type": "Researcher",
    }


def test_user_contact_response_serializes_null_optional_fields():
    user = UserFactory(phone=None, address=None, link=None)

    response = UserContactResponse.model_validate(user)
    data = response.model_dump(by_alias=True)

    assert data["phone"] is None
    assert data["address"] is None
    assert data["link"] is None
