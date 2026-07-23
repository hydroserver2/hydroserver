from django.contrib import admin

from core.iam.models import Workspace


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_private")
    list_filter = ("is_private",)
    search_fields = ("name", "owner__email")
    autocomplete_fields = ("owner",)
