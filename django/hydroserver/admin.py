from django.db import transaction
from django.http import HttpResponseRedirect
from django.core.management import call_command
from django.contrib import admin, messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.conf import settings


class HydroServerAdminSite(admin.AdminSite):
    """Admin site that delegates login, logout, and password changes to allauth."""

    @method_decorator(never_cache)
    @login_not_required
    def login(self, request, extra_context=None):
        next_url = request.GET.get(REDIRECT_FIELD_NAME, "")
        if not url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = reverse("admin:index", current_app=self.name)

        if not request.user.is_authenticated:
            return redirect_to_login(next_url)

        if not self.has_permission(request):
            messages.error(
                request, "You don't have permission to access the admin dashboard."
            )
            return redirect("account_profile")

        return HttpResponseRedirect(next_url)

    def logout(self, request, extra_context=None):
        return redirect("account_logout")

    def password_change(self, request, extra_context=None):
        return redirect("account_change_password")


class VocabularyAdmin:
    @transaction.atomic
    def load_fixtures(self, request, redirect, fixtures):
        try:
            for fixture in fixtures:
                call_command("loaddata", str(settings.BASE_DIR / fixture))
            self.message_user(
                request, "Default data loaded successfully!", messages.SUCCESS
            )
        except Exception as e:
            self.message_user(request, f"Error loading data: {str(e)}", messages.ERROR)

        return HttpResponseRedirect(reverse(redirect))
