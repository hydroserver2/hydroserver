from django.urls import path
from django.contrib import admin
from domains.etl.models import (
    OrchestrationSystem,
    DataConnection,
    Task,
    TaskMapping,
    TaskMappingPath,
    TaskRun,
)
from hydroserver.admin import VocabularyAdmin


class OrchestrationSystemAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name", "orchestration_system_type", "workspace__name")
    change_list_template = "admin/etl/orchestrationsystem/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-orchestration-system-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="orchestration_system_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:etl_orchestrationsystem_changelist",
            ["domains/etl/fixtures/default_orchestration_systems.yaml"],
        )


class DataConnectionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "data_connection_type", "workspace__name")


class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "data_connection__name", "orchestration_system__name",
                    "data_connection__workspace__name")


class TaskMappingAdmin(admin.ModelAdmin):
    list_display = ("id", "task__name", "source_identifier", "task__data_connection__name",
                    "task__data_connection__workspace__name")


class TaskMappingPathAdmin(admin.ModelAdmin):
    list_display = ("id", "task_mapping__task__name", "target_identifier", "task_mapping__task__data_connection__name",
                    "task_mapping__task__data_connection__workspace__name")


class TaskRunAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "started_at", "finished_at", "result")


admin.site.register(OrchestrationSystem, OrchestrationSystemAdmin)
admin.site.register(DataConnection, DataConnectionAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(TaskMapping, TaskMappingAdmin)
admin.site.register(TaskMappingPath, TaskMappingPathAdmin)
admin.site.register(TaskRun, TaskRunAdmin)
