from django.conf import settings
from django.contrib import admin
from django.db import transaction
from django.urls import path
from django.core.management.base import CommandError
from core.sta.models import (
    MonitoringSite,
    Method,
    ObservedProperty,
    Datastream,
    Unit,
    ProcessingLevel,
    MonitoringSiteLinkedResource,
    DatastreamLinkedResource,
    ResultQualifier,
    Observation,
    MonitoringSiteType,
    MethodType,
    ObservedPropertyType,
    UnitType,
    AggregationStatistic,
    DatastreamStatus,
    SampledMedium,
    LinkedResourceType,
)
from interfaces.actions.management.utils import generate_test_timeseries
from hydroserver.admin import VocabularyAdmin


class MonitoringSiteAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "workspace__name", "is_private")

    def delete_queryset(self, request, queryset):
        MonitoringSite.delete_contents(filter_arg=queryset, filter_suffix="in")
        queryset.delete()


class MonitoringSiteLinkedResourceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "monitoring_site__name", "monitoring_site__workspace__name")

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not settings.MEDIA_STORAGE_ENABLED:
            fields = [f for f in fields if f != "file"]
        return fields


class MethodAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "workspace__name")


class ObservedPropertyAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name", "workspace__name")
    change_list_template = "admin/sta/observedproperty/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-observed-property-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="observed_property_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_observedproperty_changelist",
            ["core/sta/fixtures/default_observed_properties.yaml"],
        )


class UnitAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name", "workspace__name")
    change_list_template = "admin/sta/unit/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-unit-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="unit_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request, "admin:sta_unit_changelist", ["core/sta/fixtures/default_units.yaml"]
        )


class ProcessingLevelAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name", "code", "workspace__name")
    change_list_template = "admin/sta/processinglevel/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-processing-level-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="processing_level_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_processinglevel_changelist",
            ["core/sta/fixtures/default_processing_levels.yaml"],
        )


class DatastreamAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "monitoring_site__name", "monitoring_site__workspace__name", "is_private")

    actions = ["populate_with_test_observations", "delete_observations"]

    def populate_with_test_observations(self, request, queryset):
        if request.user.is_superuser:
            with transaction.atomic():
                try:
                    for datastream in queryset:
                        generate_test_timeseries(datastream.id)
                except CommandError as e:
                    self.message_user(
                        request, f"An error occurred: {str(e)}", level="error"
                    )
            self.message_user(request, "Observations loaded successfully.")
        else:
            self.message_user(
                request,
                "You do not have permission to perform this action",
                level="error",
            )

    def delete_observations(self, request, queryset):
        if request.user.is_superuser:
            with transaction.atomic():
                for datastream in queryset:
                    observations = Observation.objects.filter(
                        datastream_id=datastream.id
                    )
                    observations.delete()
                    datastream.phenomenon_begin_time = None
                    datastream.phenomenon_end_time = None
                    datastream.result_begin_time = None
                    datastream.result_end_time = None
                    datastream.value_count = 0
                    datastream.save()
            self.message_user(request, "Observations deleted successfully.")
        else:
            self.message_user(
                request,
                "You do not have permission to perform this action",
                level="error",
            )

    def delete_queryset(self, request, queryset):
        Datastream.delete_contents(filter_arg=queryset, filter_suffix="in")
        queryset.delete()

    populate_with_test_observations.short_description = (
        "Populate with test observations"
    )
    delete_observations.short_description = "Delete datastream observations"


class DatastreamLinkedResourceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "datastream__name")

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not settings.MEDIA_STORAGE_ENABLED:
            fields = [f for f in fields if f != "file"]
        return fields


class ResultQualifierAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "workspace__name", "is_active")


class MonitoringSiteTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name", "workspace__name", "is_active")
    change_list_template = "admin/sta/monitoringsitetype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-monitoring-site-type-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="monitoring_site_type_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_monitoringsitetype_changelist",
            ["core/sta/fixtures/default_monitoring_site_types.yaml"],
        )


class MethodTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name", "workspace__name", "is_active")
    change_list_template = "admin/sta/methodtype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-method-type-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="method_type_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_methodtype_changelist",
            ["core/sta/fixtures/default_method_types.yaml"],
        )


class ObservedPropertyTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name", "workspace__name", "is_active")
    change_list_template = "admin/sta/observedpropertytype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-observed-property-type-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="observed_property_type_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_observedpropertytype_changelist",
            ["core/sta/fixtures/default_observed_property_types.yaml"],
        )


class UnitTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name", "workspace__name", "is_active")
    change_list_template = "admin/sta/unittype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-unit-type-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="unit_type_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_unittype_changelist",
            ["core/sta/fixtures/default_unit_types.yaml"],
        )


class AggregationStatisticAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name", "workspace__name", "is_active")
    change_list_template = "admin/sta/aggregationstatistic/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-aggregation-statistic-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="aggregation_statistic_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_aggregationstatistic_changelist",
            ["core/sta/fixtures/default_aggregation_statistics.yaml"],
        )


class DatastreamStatusAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name", "workspace__name", "is_active")
    change_list_template = "admin/sta/datastreamstatus/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-datastream-status-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="datastream_status_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_datastreamstatus_changelist",
            ["core/sta/fixtures/default_datastream_statuses.yaml"],
        )


class SampledMediumAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name", "workspace__name", "is_active")
    change_list_template = "admin/sta/sampledmedium/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-sampled-medium-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="sampled_medium_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_sampledmedium_changelist",
            ["core/sta/fixtures/default_sampled_mediums.yaml"],
        )


class LinkedResourceTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name", "workspace__name", "is_active")
    change_list_template = "admin/sta/linkedresourcetype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-linked-resource-type-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="linked_resource_type_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_linkedresourcetype_changelist",
            ["core/sta/fixtures/default_linked_resource_types.yaml"],
        )


admin.site.register(MonitoringSite, MonitoringSiteAdmin)
admin.site.register(MonitoringSiteLinkedResource, MonitoringSiteLinkedResourceAdmin)
admin.site.register(Method, MethodAdmin)
admin.site.register(ObservedProperty, ObservedPropertyAdmin)
admin.site.register(Unit, UnitAdmin)
admin.site.register(ProcessingLevel, ProcessingLevelAdmin)
admin.site.register(Datastream, DatastreamAdmin)
admin.site.register(DatastreamLinkedResource, DatastreamLinkedResourceAdmin)
admin.site.register(LinkedResourceType, LinkedResourceTypeAdmin)
admin.site.register(ResultQualifier, ResultQualifierAdmin)
admin.site.register(MonitoringSiteType, MonitoringSiteTypeAdmin)
admin.site.register(MethodType, MethodTypeAdmin)
admin.site.register(ObservedPropertyType, ObservedPropertyTypeAdmin)
admin.site.register(UnitType, UnitTypeAdmin)
admin.site.register(AggregationStatistic, AggregationStatisticAdmin)
admin.site.register(DatastreamStatus, DatastreamStatusAdmin)
admin.site.register(SampledMedium, SampledMediumAdmin)
