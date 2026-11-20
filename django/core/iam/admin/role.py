from django.contrib import admin

from core.iam.models import Role, Permission

from .mixins import LoadDefaultsMixin


class PermissionInline(admin.TabularInline):
    model = Permission
    extra = 1


@admin.register(Role)
class RoleAdmin(LoadDefaultsMixin, admin.ModelAdmin):
    default_fixture = "default_roles"
    list_display = ("name", "workspace", "description")
    search_fields = ("name",)
    autocomplete_fields = ("workspace",)
    inlines = (PermissionInline,)
