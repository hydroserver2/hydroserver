from django.http import HttpRequest
from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest):
        return settings.ACCOUNT_SIGNUP_ENABLED

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)

        if not settings.ACCOUNT_OWNERSHIP_ENABLED:
            user.owned_workspace_limit = 0
        user.save()

        return user
