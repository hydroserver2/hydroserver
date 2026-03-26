from django.urls import path
from interfaces.account import views

urlpatterns = [
    path("login/", views.login, name="account_login"),
    path("email/", views.unavailable_account_management, name="disabled_account_email"),
    path("3rdparty/", views.unavailable_account_management, name="disabled_socialaccount_connections"),
    path("social/connections/", views.unavailable_account_management, name="disabled_socialaccount_connections_legacy"),
    path("profile/", views.profile, name="account_profile"),
    path("profile/edit/", views.profile_edit, name="account_profile_edit"),
    path("profile/delete/", views.delete_account, name="account_delete"),
]
