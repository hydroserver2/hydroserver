from django import forms
from django.conf import settings

from core.iam.models import Organization, OrganizationType, UserType
from .fields import PhoneNumberField


class UserSignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, required=False, label="First name")
    middle_name = forms.CharField(max_length=30, required=False, label="Middle name")
    last_name = forms.CharField(max_length=100, required=False, label="Last name")
    phone = PhoneNumberField(max_length=15, required=False, label="Phone")
    address = forms.CharField(max_length=255, required=False, label="Address")
    link = forms.URLField(max_length=2000, required=False, label="Link")
    user_type = forms.ChoiceField(choices=[], required=True, label="Account type")

    has_organization = forms.BooleanField(
        required=False,
        label="Affiliated with an organization",
        widget=forms.CheckboxInput(
            attrs={"class": "hs-checkbox", "aria-controls": "org-fields"}
        ),
    )
    org_name = forms.CharField(max_length=255, required=False, label="Organization name")
    org_code = forms.CharField(max_length=255, required=False, label="Organization code")
    org_description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label="Organization description",
    )
    org_link = forms.URLField(max_length=2000, required=False, label="Organization link")
    org_type = forms.ChoiceField(
        choices=[], required=False, label="Organization type"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        user_types = UserType.objects.filter(public=True).values_list("name", flat=True)
        self.fields["user_type"].choices = (
            [("", "Select an account type...")] + [(t, t) for t in user_types]
            if user_types
            else [("Other", "Other")]
        )

        org_types = OrganizationType.objects.filter(public=True).values_list(
            "name", flat=True
        )
        self.fields["org_type"].choices = (
            [("", "Select an organization type...")] + [(t, t) for t in org_types]
            if org_types
            else [("Other", "Other")]
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("has_organization"):
            if not cleaned_data.get("org_name"):
                self.add_error("org_name", "Organization name is required.")
            if not cleaned_data.get("org_code"):
                self.add_error("org_code", "Organization code is required.")
            if not cleaned_data.get("org_type"):
                self.add_error("org_type", "Organization type is required.")
        return cleaned_data

    def signup(self, request, user):
        data = self.cleaned_data
        user.user_type = data["user_type"]
        for field in ("middle_name", "phone", "address", "link"):
            setattr(user, field, data.get(field) or None)

        if data.get("has_organization"):
            user.organization = Organization.objects.create(
                name=data["org_name"],
                code=data["org_code"],
                description=data.get("org_description") or None,
                link=data.get("org_link") or None,
                organization_type=data["org_type"],
            )

        if not settings.ACCOUNT_OWNERSHIP_ENABLED:
            user.owned_workspace_limit = 0

        user.save()
