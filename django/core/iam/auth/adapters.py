from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import filter_users_by_email
from allauth.core import context

PASSWORD_RESET_EMAILS = {"account/email/password_reset_key", "account/email/password_reset_code"}


def is_provider_only_user(user):
    """
    Whether password management is off for a user: SOCIALACCOUNT_SIGNUP_ONLY is
    on and the user has no password and isn't an admin.
    """

    return (
        settings.SOCIALACCOUNT_SIGNUP_ONLY
        and not user.has_usable_password()
        and not (user.is_staff or user.is_superuser)
    )


class AccountAdapter(DefaultAccountAdapter):
    def add_message(
        self,
        request,
        level,
        message_template=None,
        message_context=None,
        extra_tags="",
        message=None,
    ):
        """Account pages use inline feedback instead of queued flash messages."""
        return

    def is_safe_url(self, url):
        """Allow configured frontend destinations as login return URLs."""
        allowed_hosts = {
            context.request.get_host(),
            *settings.ALLOWED_HOSTS,
            urlparse(settings.WEB_CLIENT_URL).netloc,
            *getattr(settings, "ACCOUNT_RETURN_URL_ALLOWED_HOSTS", ()),
        }

        if "*" in allowed_hosts:
            parsed_host = urlparse(url).netloc
            allowed_hosts = {parsed_host} if parsed_host else None

        return url_has_allowed_host_and_scheme(url, allowed_hosts=allowed_hosts)

    def send_mail(self, template_prefix, email, context):
        """Tell provider-only users to sign in with their provider instead of resetting a password."""

        if template_prefix in PASSWORD_RESET_EMAILS:
            user = context.get("user") or next(
                iter(filter_users_by_email(email, is_active=True, prefer_verified=True)), None
            )
            if user and is_provider_only_user(user):
                request = context["request"]
                template_prefix = "account/email/password_reset_provider"
                context = {
                    **context,
                    "providers": [account.get_provider(request).name for account in user.socialaccount_set.all()],
                    "login_url": request.build_absolute_uri(reverse("account_login")),
                }

        return super().send_mail(template_prefix, email, context)

    def is_open_for_signup(self, request: HttpRequest):
        return settings.ACCOUNT_SIGNUP_ENABLED

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)

        if not settings.ACCOUNT_OWNERSHIP_ENABLED:
            user.owned_workspace_limit = 0
        user.save()

        return user
