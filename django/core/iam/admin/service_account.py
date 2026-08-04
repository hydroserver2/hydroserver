from django.contrib import admin

from core.iam.models import ServiceAccount


@admin.register(ServiceAccount)
class ServiceAccountAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "workspace",
        "email",
        "is_active",
        "key_expires_at",
        "last_used_at",
    )
    list_filter = ("is_active", "workspace")
    search_fields = ("name", "email",)
    autocomplete_fields = ("workspace",)
    readonly_fields = ("email", "key_prefix", "key_hash", "key_created_at",)
