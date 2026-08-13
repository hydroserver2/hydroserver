from django.core.exceptions import ValidationError


def validate_tags(value):
    if not isinstance(value, dict) or any(
        not isinstance(key, str) or not isinstance(val, str) or not key or not val
        for key, val in value.items()
    ):
        raise ValidationError("Tags must be an object with non-empty string values.")
