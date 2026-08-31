from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpRequest
from django.utils.http import url_has_allowed_host_and_scheme
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context


class AccountAdapter(DefaultAccountAdapter):
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

    def is_open_for_signup(self, request: HttpRequest):
        return settings.ACCOUNT_SIGNUP_ENABLED

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)

        if not settings.ACCOUNT_OWNERSHIP_ENABLED:
            user.owned_workspace_limit = 0
        user.save()

        return user
