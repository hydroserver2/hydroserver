import logging
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from interfaces.account.forms import ProfileForm, DeleteAccountForm
from domains.iam.services import AccountService


logger = logging.getLogger(__name__)
account_service = AccountService()


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
def delete_account(request):
    user = request.user
    owned_workspaces = []
    try:
        from domains.iam.models import Workspace
        owned_workspaces = list(
            Workspace.objects.filter(owner=user).values_list("name", flat=True)
        )
    except Exception:
        logger.exception("Failed to load owned workspaces")

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
