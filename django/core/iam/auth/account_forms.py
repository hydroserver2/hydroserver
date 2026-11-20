"""
allauth form overrides for SOCIALACCOUNT_SIGNUP_ONLY. Kept apart from forms.py
because allauth's forms import ACCOUNT_SIGNUP_FORM_CLASS from there.
"""

from allauth.account import forms as allauth_forms
from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from core.iam.auth.adapters import is_provider_only_user


class SignupForm(allauth_forms.SignupForm):
    def clean(self):
        if settings.SOCIALACCOUNT_SIGNUP_ONLY:
            raise forms.ValidationError(_("Sign up with one of the providers below."))
        return super().clean()


class SetPasswordForm(allauth_forms.SetPasswordForm):
    def clean(self):
        if is_provider_only_user(self.user):
            raise forms.ValidationError(_("Sign in with your provider instead of setting a password."))
        return super().clean()
