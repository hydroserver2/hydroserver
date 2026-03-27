import logging
from urllib.parse import unquote

from allauth.account.views import LoginView as AllauthLoginView
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import OperationalError, ProgrammingError
from django.shortcuts import render, redirect
from django.contrib import messages
from interfaces.account.forms import ProfileForm, DeleteAccountForm
from domains.iam.services import AccountService


logger = logging.getLogger(__name__)
account_service = AccountService()


def _normalize_redirect_field(query_dict):
    if REDIRECT_FIELD_NAME not in query_dict:
        return query_dict

    raw_value = query_dict.get(REDIRECT_FIELD_NAME)
    if not raw_value:
        return query_dict

    decoded_value = unquote(raw_value)
    if decoded_value == raw_value:
        return query_dict

    normalized = query_dict.copy()
    normalized[REDIRECT_FIELD_NAME] = decoded_value
    return normalized


class LoginView(AllauthLoginView):
    def dispatch(self, request, *args, **kwargs):
        request.GET = _normalize_redirect_field(request.GET)
        if request.method == "POST":
            request.POST = _normalize_redirect_field(request.POST)
        return super().dispatch(request, *args, **kwargs)


login = LoginView.as_view()


@login_required
def profile(request):
    user = request.user
    return render(request, "account/profile.html", {
        "user": user,
        "organization": user.organization,
    })


@login_required
def profile_edit(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("account_profile")
    else:
        form = ProfileForm(instance=request.user)

    return render(request, "account/profile_edit.html", {"form": form})


@login_required
def unavailable_account_management(request):
    messages.info(request, "That account management page is not available in this HydroServer instance.")
    return redirect("account_profile")


@login_required
def delete_account(request):
    user = request.user
    owned_workspaces = []
    try:
        from domains.iam.models import Workspace
        owned_workspaces = list(
            Workspace.objects.filter(owner=user).values_list("name", flat=True)
        )
    except (OperationalError, ProgrammingError):
        logger.exception("Failed to load owned workspaces")
        messages.warning(request, "Could not load your workspace list. Proceed with caution.")

    if request.method == "POST":
        form = DeleteAccountForm(request.POST)
        if form.is_valid():
            account_service.delete(user)
            logout(request)
            messages.success(request, "Your account has been deleted.")
            return redirect("account_login")
    else:
        form = DeleteAccountForm()

    return render(request, "account/delete_account.html", {
        "form": form,
        "owned_workspaces": owned_workspaces,
    })
