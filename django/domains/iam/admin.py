from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import path
from domains.iam.models import (
    User,
    UserType,
    Organization,
    OrganizationType,
    Workspace,
    Role,
    Permission,
    Collaborator,
    APIKey,
)
from hydroserver.admin import VocabularyAdmin


class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "account_type", "is_active")

    def delete_queryset(self, request, queryset):
        User.delete_contents(filter_arg=queryset, filter_suffix="in")
        queryset.delete()


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


class UserTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name")
    change_list_template = "admin/iam/usertype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-user-type-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="user_type_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:iam_usertype_changelist",
            ["domains/iam/fixtures/default_user_types.yaml"],
        )


class OrganizationTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name")
    change_list_template = "admin/iam/organizationtype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-organization-type-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="organization_type_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:iam_organizationtype_changelist",
            ["domains/iam/fixtures/default_organization_types.yaml"],
        )


class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "is_private")

    def delete_queryset(self, request, queryset):
        Workspace.delete_contents(filter_arg=queryset, filter_suffix="in")
        queryset.delete()


class RoleAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name", "workspace__name")
    change_list_template = "admin/iam/role/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-role-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="role_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request, "admin:iam_role_changelist", ["domains/iam/fixtures/default_roles.yaml"]
        )

    def delete_queryset(self, request, queryset):
        Role.delete_contents(filter_arg=queryset, filter_suffix="in")
        queryset.delete()


class PermissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "role__name",
        "permission_type",
        "resource_type",
        "role__workspace__name",
    )


class CollaboratorAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "role__name", "workspace__name")


class APIKeyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "role__name",
        "is_active",
        "last_used",
        "expires_at",
        "workspace__name",
    )

    def regenerate_api_key(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                "Please select exactly one API key to regenerate.",
                level=messages.ERROR,
            )
            return

        apikey = queryset.first()
        new_key = apikey.generate_key()

        self.message_user(
            request,
            format_html("New API key: <code>{}</code>", new_key),
            level=messages.SUCCESS,
        )

    actions = ["regenerate_api_key"]
    regenerate_api_key.short_description = "Regenerate selected API key"


admin.site.register(User, UserAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(UserType, UserTypeAdmin)
admin.site.register(OrganizationType, OrganizationTypeAdmin)
admin.site.register(Workspace, WorkspaceAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Permission, PermissionAdmin)
admin.site.register(Collaborator, CollaboratorAdmin)
admin.site.register(APIKey, APIKeyAdmin)
