from django.contrib import admin
from django.db import transaction
from django.urls import path
from django.core.management.base import CommandError
from domains.sta.models import (
    Thing,
    Sensor,
    ObservedProperty,
    Datastream,
    Location,
    Unit,
    ProcessingLevel,
    ThingFileAttachment,
    ThingTag,
    DatastreamFileAttachment,
    DatastreamTag,
    ResultQualifier,
    Observation,
    SiteType,
    SamplingFeatureType,
    MethodType,
    SensorEncodingType,
    VariableType,
    UnitType,
    DatastreamAggregation,
    DatastreamStatus,
    SampledMedium,
    FileAttachmentType,
)
from interfaces.actions.management.utils import generate_test_timeseries
from hydroserver.admin import VocabularyAdmin


class ThingAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "workspace__name", "is_private")

    def delete_queryset(self, request, queryset):
        Thing.delete_contents(filter_arg=queryset, filter_suffix="in")
        queryset.delete()


class LocationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "thing__name", "thing__workspace__name")


class ThingFileAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "thing__name", "thing__workspace__name")


class ThingTagAdmin(admin.ModelAdmin):
    list_display = ("id", "key", "value", "thing__name", "thing__workspace__name")


class SensorAdmin(admin.ModelAdmin):
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
            ["domains/sta/fixtures/default_observed_properties.yaml"],
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
            request, "admin:sta_unit_changelist", ["domains/sta/fixtures/default_units.yaml"]
        )


class ProcessingLevelAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "code", "workspace__name")
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
            ["domains/sta/fixtures/default_processing_levels.yaml"],
        )


class DatastreamAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "thing__name", "thing__workspace__name", "is_private")

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


class DatastreamFileAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "datastream__name")


class DatastreamTagAdmin(admin.ModelAdmin):
    list_display = ("id", "key", "value", "datastream__name")


class ResultQualifierAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "workspace__name")


class SiteTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name")
    change_list_template = "admin/sta/sitetype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-site-type-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="site_type_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_sitetype_changelist",
            ["domains/sta/fixtures/default_site_types.yaml"],
        )


class SamplingFeatureTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name")
    change_list_template = "admin/sta/samplingfeaturetype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-sampling-feature-type-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="sampling_feature_type_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_samplingfeaturetype_changelist",
            ["domains/sta/fixtures/default_sampling_feature_types.yaml"],
        )


class MethodTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name")
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
            ["domains/sta/fixtures/default_method_types.yaml"],
        )


class SensorEncodingTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name")
    change_list_template = "admin/sta/sensorencodingtype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-sensor-encoding-type-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="sensor_encoding_type_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_sensorencodingtype_changelist",
            ["domains/sta/fixtures/default_sensor_encoding_types.yaml"],
        )


class VariableTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name")
    change_list_template = "admin/sta/variabletype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-variable-type-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="variable_type_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_variabletype_changelist",
            ["domains/sta/fixtures/default_variable_types.yaml"],
        )


class UnitTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name")
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
            ["domains/sta/fixtures/default_unit_types.yaml"],
        )


class DatastreamAggregationAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name")
    change_list_template = "admin/sta/datastreamaggregation/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-datastream-aggregation-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="datastream_aggregation_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_datastreamaggregation_changelist",
            ["domains/sta/fixtures/default_datastream_aggregations.yaml"],
        )


class DatastreamStatusAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name")
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
            ["domains/sta/fixtures/default_datastream_statuses.yaml"],
        )


class SampledMediumAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name")
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
            ["domains/sta/fixtures/default_sampled_mediums.yaml"],
        )


class FileAttachmentTypeAdmin(admin.ModelAdmin, VocabularyAdmin):
    list_display = ("id", "name")
    change_list_template = "admin/sta/fileattachmenttype/change_list.html"

    def get_urls(self):
        urls = super().get_urls()

        return [
            path(
                "load-default-file-attachment-type-data/",
                self.admin_site.admin_view(self.load_default_data),
                name="file_attachment_type_load_default_data",
            ),
        ] + urls

    def load_default_data(self, request):
        return self.load_fixtures(
            request,
            "admin:sta_fileattachmenttype_changelist",
            ["domains/sta/fixtures/default_file_attachment_types.yaml"],
        )


admin.site.register(Thing, ThingAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(ThingFileAttachment, ThingFileAttachmentAdmin)
admin.site.register(ThingTag, ThingTagAdmin)
admin.site.register(Sensor, SensorAdmin)
admin.site.register(ObservedProperty, ObservedPropertyAdmin)
admin.site.register(Unit, UnitAdmin)
admin.site.register(ProcessingLevel, ProcessingLevelAdmin)
admin.site.register(Datastream, DatastreamAdmin)
admin.site.register(DatastreamFileAttachment, DatastreamFileAttachmentAdmin)
admin.site.register(DatastreamTag, DatastreamTagAdmin)
admin.site.register(FileAttachmentType, FileAttachmentTypeAdmin)
admin.site.register(ResultQualifier, ResultQualifierAdmin)
admin.site.register(SiteType, SiteTypeAdmin)
admin.site.register(SamplingFeatureType, SamplingFeatureTypeAdmin)
admin.site.register(MethodType, MethodTypeAdmin)
admin.site.register(VariableType, VariableTypeAdmin)
admin.site.register(SensorEncodingType, SensorEncodingTypeAdmin)
admin.site.register(UnitType, UnitTypeAdmin)
admin.site.register(DatastreamAggregation, DatastreamAggregationAdmin)
admin.site.register(DatastreamStatus, DatastreamStatusAdmin)
admin.site.register(SampledMedium, SampledMediumAdmin)
