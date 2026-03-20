from django import forms
from django.conf import settings
from interfaces.auth.schemas import AccountPatchBody
from domains.iam.services import AccountService


class UserSignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, required=False, label="firstName")
    middle_name = forms.CharField(max_length=30, required=False, label="middleName")
    last_name = forms.CharField(max_length=100, required=False, label="lastName")
    phone = forms.CharField(max_length=15, required=False)
    address = forms.CharField(max_length=255, required=False)
    link = forms.URLField(max_length=2000, required=False)
    user_type = forms.CharField(max_length=255, required=True, label="type")
    organization = forms.JSONField(required=False)

    def __init__(self, *args, **kwargs):
        if "data" in kwargs:
            data = kwargs["data"].copy()
            for field_name, field in self.base_fields.items():
                alias = field.label or field_name
                if alias in data:
                    data[field_name] = data.pop(alias)
            kwargs["data"] = data
        super().__init__(*args, **kwargs)

    def signup(self, request, user):
        account = AccountPatchBody(**self.cleaned_data)
        AccountService.update(principal=user, data=account)
        user.is_ownership_allowed = settings.ACCOUNT_OWNERSHIP_ENABLED
        user.save()
