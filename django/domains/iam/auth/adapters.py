from django.http import HttpRequest
from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter
from interfaces.auth.schemas import AccountPatchBody
from domains.iam.services import AccountService


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest):
        return settings.ACCOUNT_SIGNUP_ENABLED

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        data = form.cleaned_data

        account = AccountPatchBody(
            **{
                "middle_name": data.get("middle_name") or None,
                "phone": data.get("phone") or None,
                "address": data.get("address") or None,
                "link": data.get("link") or None,
                "user_type": data.get("user_type") or None,
                "organization": data.get("organization") or None,
            }
        )
        user = AccountService.update(principal=user, data=account)
        user.is_ownership_allowed = settings.ACCOUNT_OWNERSHIP_ENABLED
        user.save()

        return user
