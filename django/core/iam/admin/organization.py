from django.contrib import admin

from core.iam.models import Organization, OrganizationType

from .mixins import LoadDefaultsMixin


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization_type", "user")
    list_filter = ("organization_type",)
    search_fields = ("name", "code", "user__email")

    @admin.display(description="User", ordering="user__email")
    def user(self, obj):
        return getattr(obj, "user", None)


@admin.register(OrganizationType)
class OrganizationTypeAdmin(LoadDefaultsMixin, admin.ModelAdmin):
    default_fixture = "default_organization_types"
    list_display = ("name", "public")
    list_editable = ("public",)
    search_fields = ("name",)
