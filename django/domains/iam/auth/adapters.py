from django.http import HttpRequest
from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter, get_adapter as get_account_adapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
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


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = sociallogin.user
        user.set_unusable_password()

        account_adapter = get_account_adapter(request)
        if form:
            account_adapter.save_user(request, user, form)
        else:
            account_adapter.populate_username(request, user)

        sociallogin.save(request)
        return user
