from django.contrib import admin
from processing.etl.models import (
    DataConnection,
    PlaceholderVariable,
    Payload,
    DataConnectionNotificationRecipient,
    EtlTask,
    EtlMapping,
)


class DataConnectionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "workspace__name", "source_url")


class PlaceholderVariableAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "data_connection__name", "variable_type")


class PayloadAdmin(admin.ModelAdmin):
    list_display = ("id", "data_connection__name", "payload_type")


class DataConnectionNotificationRecipientAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "notification__data_connection__name")


class EtlTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "data_connection__name")


class EtlMappingAdmin(admin.ModelAdmin):
    list_display = ("id", "source_identifier", "etl_task__name", "target_datastream__name")


admin.site.register(DataConnection, DataConnectionAdmin)
admin.site.register(PlaceholderVariable, PlaceholderVariableAdmin)
admin.site.register(Payload, PayloadAdmin)
admin.site.register(DataConnectionNotificationRecipient, DataConnectionNotificationRecipientAdmin)
admin.site.register(EtlTask, EtlTaskAdmin)
admin.site.register(EtlMapping, EtlMappingAdmin)
