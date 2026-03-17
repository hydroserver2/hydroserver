from django.contrib import admin
from domains.web.models import (
    InstanceConfiguration,
    MapConfiguration,
    AnalyticsConfiguration,
    MapLayer,
    ContactInformation,
)


class ContactInformationAdmin(admin.ModelAdmin):
    list_display = ("title", "link")


class MapLayerAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "priority", "source", "attribution")


admin.site.register(InstanceConfiguration)
admin.site.register(MapConfiguration)
admin.site.register(AnalyticsConfiguration)
admin.site.register(MapLayer, MapLayerAdmin)
admin.site.register(ContactInformation, ContactInformationAdmin)
