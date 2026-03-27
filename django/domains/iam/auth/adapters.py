import logging
from smtplib import SMTPException
from urllib.parse import urlparse

from django.http import HttpRequest
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import get_connection
from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter, get_adapter as get_account_adapter
from allauth.core import context as allauth_context
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from interfaces.account.navigation import get_post_auth_account_return_to
from interfaces.auth.schemas import AccountPatchBody
from domains.iam.services import AccountService


logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    def get_logout_redirect_url(self, request: HttpRequest) -> str:
        return reverse("account_login")

    def is_open_for_signup(self, request: HttpRequest):
        return settings.ACCOUNT_SIGNUP_ENABLED

    def get_login_redirect_url(self, request):
        return get_post_auth_account_return_to(request) or super().get_login_redirect_url(
            request
        )

    def get_signup_redirect_url(self, request):
        return get_post_auth_account_return_to(request) or super().get_signup_redirect_url(
            request
        )

    def get_email_verification_redirect_url(self, email_address):
        request = allauth_context.request
        if request is not None:
            redirect_url = get_post_auth_account_return_to(request)
            if redirect_url:
                return redirect_url
        return super().get_email_verification_redirect_url(email_address)

    def is_safe_url(self, url):
        parsed = urlparse(url)
        try:
            if super().is_safe_url(url):
                return True
        except (AttributeError, LookupError):
            if parsed.scheme or parsed.netloc:
                pass
            else:
                return url.startswith("/") and not url.startswith("//")

        if not parsed.scheme or not parsed.netloc:
            return False

        return self._origin_from_url(url) in self._get_allowed_return_origins()

    def send_mail(self, template_prefix: str, email: str, context: dict) -> None:
        request = allauth_context.request
        ctx = {
            "request": request,
            "email": email,
            "current_site": get_current_site(request),
        }
        ctx.update(context)
        msg = self.render_mail(template_prefix, email, ctx)
        try:
            msg.send()
        except (OSError, SMTPException):
            if settings.DEPLOYMENT_BACKEND not in {"dev", "local"}:
                raise
            logger.exception(
                "SMTP delivery failed in %s; falling back to console email backend.",
                settings.DEPLOYMENT_BACKEND,
            )
            console_connection = get_connection(
                backend="django.core.mail.backends.console.EmailBackend"
            )
            console_connection.send_messages([msg])

    def _get_allowed_return_origins(self):
        origins = set()

        for client_config in getattr(settings, "OIDC_BUNDLED_CLIENTS", {}).values():
            for url in client_config.get("redirect_uris", []):
                origin = self._origin_from_url(url)
                if origin:
                    origins.add(origin)
            for origin in client_config.get("cors_origins", []):
                normalized = self._origin_from_url(origin)
                if normalized:
                    origins.add(normalized)

        return origins

    @staticmethod
    def _origin_from_url(url):
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

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
            extra_data = sociallogin.account.extra_data or {}
            if not user.first_name:
                user.first_name = extra_data.get("given_name", "")
            if not user.last_name:
                user.last_name = extra_data.get("family_name", "")
            if not user.user_type:
                user.user_type = "Unspecified"
            user.is_ownership_allowed = settings.ACCOUNT_OWNERSHIP_ENABLED
            user.save()

        sociallogin.save(request)
        return user
