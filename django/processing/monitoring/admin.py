from django.contrib import admin
from processing.monitoring.models import (
    MonitoringTask,
    MonitoringNotificationRecipient,
    MonitoringRule,
)


class MonitoringTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "thing__name", "thing__workspace__name")


class MonitoringNotificationRecipientAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "task__name")


class MonitoringRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "rule_type", "task__name", "datastream__name")


admin.site.register(MonitoringTask, MonitoringTaskAdmin)
admin.site.register(MonitoringNotificationRecipient, MonitoringNotificationRecipientAdmin)
admin.site.register(MonitoringRule, MonitoringRuleAdmin)
