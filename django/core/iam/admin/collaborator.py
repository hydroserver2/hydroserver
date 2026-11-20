from django.contrib import admin

from core.iam.models import Collaborator


@admin.register(Collaborator)
class CollaboratorAdmin(admin.ModelAdmin):
    list_display = ("workspace", "principal", "role")
    list_filter = ("workspace", "role")
    autocomplete_fields = ("workspace", "user", "service_account", "role")

    @admin.display(description="Principal")
    def principal(self, obj):
        return obj.user or obj.service_account
