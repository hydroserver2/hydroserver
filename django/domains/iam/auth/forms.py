from django import forms
from django.conf import settings

from interfaces.auth.schemas import AccountPatchBody
from domains.iam.models import OrganizationType, UserType
from domains.iam.services import AccountService


class UserSignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, required=False, label="firstName")
    middle_name = forms.CharField(max_length=30, required=False, label="middleName")
    last_name = forms.CharField(max_length=100, required=False, label="lastName")
    phone = forms.CharField(max_length=15, required=False)
    address = forms.CharField(max_length=255, required=False)
    link = forms.URLField(max_length=2000, required=False)
    user_type = forms.CharField(max_length=255, required=True, label="type")
    has_organization = forms.BooleanField(required=False, label="Affiliated with an organization")
    org_name = forms.CharField(max_length=255, required=False, label="Organization name")
    org_code = forms.CharField(max_length=255, required=False, label="Organization code")
    org_description = forms.CharField(
        required=False,
        label="Organization description",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    org_link = forms.URLField(max_length=2000, required=False, label="Organization link")
    org_type = forms.CharField(max_length=255, required=False, label="Organization type")
    organization = forms.JSONField(required=False)

    def __init__(self, *args, **kwargs):
        if "data" in kwargs:
            data = kwargs["data"].copy()
            for field_name, field in self.base_fields.items():
                alias = field.label or field_name
                if alias in data:
                    data[field_name] = data.pop(alias)
            organization = data.get("organization")
            if isinstance(organization, dict):
                data.setdefault("has_organization", "on")
                data.setdefault("org_name", organization.get("name", ""))
                data.setdefault("org_code", organization.get("code", ""))
                data.setdefault("org_description", organization.get("description", ""))
                data.setdefault("org_link", organization.get("link", ""))
                data.setdefault(
                    "org_type",
                    organization.get("type") or organization.get("organization_type", ""),
                )
            kwargs["data"] = data
        super().__init__(*args, **kwargs)

        user_types = list(UserType.objects.filter(public=True).values_list("name", flat=True))
        if user_types:
            self.fields["user_type"] = forms.ChoiceField(
                choices=[("", "Select a type...")] + [(user_type, user_type) for user_type in user_types],
                required=True,
                label="type",
            )

        organization_types = list(
            OrganizationType.objects.filter(public=True).values_list("name", flat=True)
        )
        if organization_types:
            self.fields["org_type"] = forms.ChoiceField(
                choices=[("", "Select a type...")] + [(org_type, org_type) for org_type in organization_types],
                required=False,
                label="Organization type",
            )

        self.fields["organization"].widget = forms.HiddenInput()
        self._configure_widgets()

    def _configure_widgets(self):
        input_class = (
            "block w-full rounded-lg border border-gray-300 bg-white px-4 py-3.5 text-sm text-gray-900 "
            "placeholder:text-gray-500 transition-colors focus:border-primary focus:outline-none "
            "focus:ring-2 focus:ring-primary/30 disabled:bg-gray-50 disabled:text-gray-500"
        )
        select_class = (
            "block w-full rounded-lg border border-gray-300 bg-white px-4 py-3.5 pr-10 text-sm text-gray-900 "
            "transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30 "
            "disabled:bg-gray-50 disabled:text-gray-500"
        )
        textarea_class = (
            "block w-full rounded-lg border border-gray-300 bg-white px-4 py-3.5 text-sm text-gray-900 "
            "placeholder:text-gray-500 transition-colors focus:border-primary focus:outline-none "
            "focus:ring-2 focus:ring-primary/30 disabled:bg-gray-50 disabled:text-gray-500"
        )

        placeholders = {
            "first_name": "First name",
            "middle_name": "Middle name",
            "last_name": "Last name",
            "email": "Email",
            "password1": "Password",
            "password2": "Confirm password",
            "phone": "Phone number",
            "address": "Address",
            "link": "User link (URL)",
            "org_name": "Organization name",
            "org_code": "Organization code",
            "org_description": "Organization description",
            "org_link": "Organization link",
        }

        for field_name, placeholder in placeholders.items():
            field = self.fields.get(field_name)
            if not field:
                continue
            field.widget.attrs["placeholder"] = placeholder
            field.widget.attrs["class"] = textarea_class if isinstance(field.widget, forms.Textarea) else input_class

        for field_name in ["user_type", "org_type"]:
            field = self.fields.get(field_name)
            if not field:
                continue
            field.widget.attrs["class"] = select_class

        has_organization_field = self.fields.get("has_organization")
        if has_organization_field:
            has_organization_field.widget.attrs["class"] = (
                "h-5 w-5 rounded border-gray-300 text-primary focus:ring-2 focus:ring-primary/40"
            )

    def clean(self):
        cleaned_data = super().clean()

        organization = cleaned_data.get("organization")
        if not isinstance(organization, dict):
            organization = {}

        has_organization = cleaned_data.get("has_organization")
        organization_name = cleaned_data.get("org_name") or organization.get("name") or ""
        organization_code = cleaned_data.get("org_code") or organization.get("code") or ""
        organization_description = (
            cleaned_data.get("org_description") or organization.get("description") or ""
        )
        organization_link = cleaned_data.get("org_link") or organization.get("link") or ""
        organization_type = (
            cleaned_data.get("org_type")
            or organization.get("type")
            or organization.get("organization_type")
            or ""
        )

        has_organization_details = any(
            [
                organization_name,
                organization_code,
                organization_description,
                organization_link,
                organization_type,
            ]
        )

        if has_organization or has_organization_details:
            if not organization_name:
                self.add_error("org_name", "Organization name is required.")
            if not organization_code:
                self.add_error("org_code", "Organization code is required.")
            if not organization_type:
                self.add_error("org_type", "Organization type is required.")

            cleaned_data["organization"] = {
                "name": organization_name,
                "code": organization_code,
                "description": organization_description or None,
                "link": organization_link or None,
                "type": organization_type,
            }
        else:
            cleaned_data["organization"] = None

        return cleaned_data

    def signup(self, request, user):
        account = AccountPatchBody(**self.cleaned_data)
        AccountService.update(principal=user, data=account)
        user.is_ownership_allowed = settings.ACCOUNT_OWNERSHIP_ENABLED
        user.save()
