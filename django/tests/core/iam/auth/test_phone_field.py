import pytest
from django.core.exceptions import ValidationError

from core.iam.auth.fields import PhoneNumberField


@pytest.mark.parametrize(
    "phone", ["", "8015551234", "801-555-1234", "(801) 555-1234", "+801 555 1234"]
)
def test_phone_field_accepts_v1_formats_without_changing_storage(phone):
    field = PhoneNumberField(max_length=15, required=False)

    assert field.clean(phone) == phone


@pytest.mark.parametrize("phone", ["123", "18015551234", "8015551234abc", "801.555.1234"])
def test_phone_field_rejects_values_disallowed_by_v1(phone):
    field = PhoneNumberField(max_length=15, required=False)

    with pytest.raises(ValidationError):
        field.clean(phone)
