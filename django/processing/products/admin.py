from django.contrib import admin
from processing.products.models import (
    RatingCurve,
    RatingCurvePoint,
    DataProductTask,
    DataProductTransformation,
    DataProductTransformationInput,
)


class RatingCurveAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "thing__name", "thing__workspace__name", "fitting_method")


class RatingCurvePointAdmin(admin.ModelAdmin):
    list_display = ("id", "rating_curve__name", "input_value", "output_value")


class DataProductTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "thing__name", "thing__workspace__name")


class DataProductTransformationAdmin(admin.ModelAdmin):
    list_display = ("id", "transformation_type", "task__name", "output_datastream__name")


class DataProductTransformationInputAdmin(admin.ModelAdmin):
    list_display = ("id", "transformation__id", "datastream__name", "variable_name")


admin.site.register(RatingCurve, RatingCurveAdmin)
admin.site.register(RatingCurvePoint, RatingCurvePointAdmin)
admin.site.register(DataProductTask, DataProductTaskAdmin)
admin.site.register(DataProductTransformation, DataProductTransformationAdmin)
admin.site.register(DataProductTransformationInput, DataProductTransformationInputAdmin)