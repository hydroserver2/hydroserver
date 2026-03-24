from django.contrib import admin
from processing.etl.models import (
    DataConnection,
    DataConnectionNotificationRecipient,
    Task,
    TaskMapping,
    TaskMappingPath,
    TaskRun,
)


class DataConnectionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "data_connection_type", "workspace__name")


class DataConnectionNotificationRecipientAdmin(admin.ModelAdmin):
    list_display = ("id", "data_connection__name", "email")


class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "data_connection__name", "data_connection__workspace__name")


class TaskMappingAdmin(admin.ModelAdmin):
    list_display = ("id", "task__name", "source_identifier", "task__data_connection__name",
                    "task__data_connection__workspace__name")


class TaskMappingPathAdmin(admin.ModelAdmin):
    list_display = ("id", "task_mapping__task__name", "target_identifier", "task_mapping__task__data_connection__name",
                    "task_mapping__task__data_connection__workspace__name")


class TaskRunAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "started_at", "finished_at", "result")


admin.site.register(DataConnection, DataConnectionAdmin)
admin.site.register(DataConnectionNotificationRecipient, DataConnectionNotificationRecipientAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(TaskMapping, TaskMappingAdmin)
admin.site.register(TaskMappingPath, TaskMappingPathAdmin)
admin.site.register(TaskRun, TaskRunAdmin)
