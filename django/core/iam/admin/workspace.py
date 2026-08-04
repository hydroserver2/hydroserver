from django.contrib import admin
from django.utils.text import capfirst

from core.iam.models import Workspace
from core.sta.models import Datastream


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_private")
    list_filter = ("is_private",)
    search_fields = ("name", "owner__email")
    autocomplete_fields = ("owner",)

    def get_deleted_objects(self, objs, request):
        to_delete, model_count, perms_needed, protected = super().get_deleted_objects(
            objs, request
        )

        datastream_prefix = f"{capfirst(Datastream._meta.verbose_name)}: "
        protected = [
            entry for entry in protected if not entry.startswith(datastream_prefix)
        ]

        return to_delete, model_count, perms_needed, protected
