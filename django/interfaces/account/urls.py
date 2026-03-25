from django.urls import path
from interfaces.account import views

urlpatterns = [
    path("profile/", views.profile, name="account_profile"),
    path("profile/edit/", views.profile_edit, name="account_profile_edit"),
    path("profile/delete/", views.delete_account, name="account_delete"),
]
