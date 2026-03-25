from django import forms
from django.contrib.auth import get_user_model
from domains.iam.models import Organization, UserType, OrganizationType

User = get_user_model()


class ProfileForm(forms.ModelForm):
    has_organization = forms.BooleanField(required=False, label="Affiliated with an organization")
    org_name = forms.CharField(max_length=255, required=False, label="Organization name")
    org_code = forms.CharField(max_length=255, required=False, label="Organization code")
    org_description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}), required=False, label="Organization description"
    )
    org_link = forms.URLField(max_length=2000, required=False, label="Organization link")
    org_type = forms.CharField(max_length=255, required=False, label="Organization type")

    class Meta:
        model = User
        fields = [
            "first_name", "middle_name", "last_name",
            "phone", "address", "link", "user_type",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        user_types = UserType.objects.filter(public=True).values_list("name", flat=True)
        self.fields["user_type"] = forms.ChoiceField(
            choices=[("", "Select a type...")] + [(t, t) for t in user_types],
            required=True,
            label="User type",
        )

        org_types = OrganizationType.objects.filter(public=True).values_list("name", flat=True)
        self.fields["org_type"] = forms.ChoiceField(
            choices=[("", "Select a type...")] + [(t, t) for t in org_types],
            required=False,
            label="Organization type",
        )

        if self.instance and self.instance.organization:
            org = self.instance.organization
            self.fields["has_organization"].initial = True
            self.fields["org_name"].initial = org.name
            self.fields["org_code"].initial = org.code
            self.fields["org_description"].initial = org.description
            self.fields["org_link"].initial = org.link
            self.fields["org_type"].initial = org.organization_type

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

    def save(self, commit=True):
        user = super().save(commit=False)

        if self.cleaned_data.get("has_organization"):
            org_data = {
                "name": self.cleaned_data["org_name"],
                "code": self.cleaned_data["org_code"],
                "description": self.cleaned_data.get("org_description") or None,
                "link": self.cleaned_data.get("org_link") or None,
                "organization_type": self.cleaned_data["org_type"],
            }
            if user.organization:
                for field, value in org_data.items():
                    setattr(user.organization, field, value)
                user.organization.save()
            else:
                user.organization = Organization.objects.create(**org_data)
        else:
            if user.organization:
                user.organization.delete()
                user.organization = None

        if commit:
            user.save()
        return user


class DeleteAccountForm(forms.Form):
    confirmation = forms.CharField(
        label='Type "delete my account and data" to confirm',
        max_length=100,
    )

    def clean_confirmation(self):
        value = self.cleaned_data["confirmation"]
        if value.strip().lower() != "delete my account and data":
            raise forms.ValidationError("Confirmation text does not match.")
        return value
