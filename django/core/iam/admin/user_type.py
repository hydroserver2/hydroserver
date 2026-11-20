from django.contrib import admin

from core.iam.models import UserType

from .mixins import LoadDefaultsMixin


@admin.register(UserType)
class UserTypeAdmin(LoadDefaultsMixin, admin.ModelAdmin):
    default_fixture = "default_user_types"
    list_display = ("name", "public")
    list_editable = ("public",)
    search_fields = ("name",)
