import re

from django import forms


class PhoneNumberInput(forms.TextInput):
    input_type = "tel"

    def __init__(self, attrs=None):
        super().__init__({
            "class": "hs-field__input",
            "inputmode": "numeric",
            "autocomplete": "tel-national",
            "placeholder": "(123) 456-7890",
            "data-maska": "(###) ###-####",
            **(attrs or {}),
        })

    class Media:
        js = ["vendor/maska/maska-3.2.0.js", "js/phone-input.js"]


class PhoneNumberField(forms.CharField):
    widget = PhoneNumberInput

    def validate(self, value):
        super().validate(value)
        if not value:
            return
        # Match the v1 AccountForm's rules.phoneNumber without changing storage.
        if len(re.sub(r"[^0-9]", "", value)) != 10:
            raise forms.ValidationError("Phone number must contain 10 digits.")
        if not re.fullmatch(r"[0-9+()\s-]*", value):
            raise forms.ValidationError(
                "Phone number can only contain digits, plus sign, parentheses, "
                "hyphens, and spaces."
            )
