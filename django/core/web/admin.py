from django import forms
from django.contrib import admin
from django.utils.html import format_html
from core.web.models import (
    InstanceConfiguration,
    MapConfiguration,
    AnalyticsConfiguration,
    MapLayer,
    ContactInformation,
    SiteTypeIcon,
)

MDI_SVG_BASE_URL = "https://cdn.jsdelivr.net/npm/@mdi/svg@7.4.47/svg"


class ContactInformationAdmin(admin.ModelAdmin):
    list_display = ("title", "link")


class MapLayerAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "priority", "source", "attribution")


class SiteTypeIconAdminForm(forms.ModelForm):
    site_types = forms.CharField(
        label="Site type names and keywords",
        required=False,
        widget=forms.Textarea(attrs={"rows": 8, "cols": 60}),
        help_text=(
            "Enter one site type name or keyword per line. Matching ignores case and "
            "punctuation; longer matches take precedence. The default entries may be "
            "changed or removed, and the list may be left empty."
        ),
    )

    class Meta:
        model = SiteTypeIcon
        fields = ("site_types",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial["site_types"] = "\n".join(self.instance.site_types)

    def clean_site_types(self):
        return [
            site_type.strip()
            for site_type in self.cleaned_data["site_types"].splitlines()
            if site_type.strip()
        ]


class SiteTypeIconAdmin(admin.ModelAdmin):
    form = SiteTypeIconAdminForm
    fields = ("icon_preview", "icon", "site_types")
    readonly_fields = ("icon_preview", "icon")
    list_display = ("icon_preview", "icon_name", "mapped_site_types")
    list_display_links = ("icon_preview", "icon_name", "mapped_site_types")

    @admin.display(description="Preview")
    def icon_preview(self, obj):
        if not obj:
            return ""
        return format_html(
            '<img class="site-type-icon-preview" src="{}/{}.svg" '
            'width="28" height="28" alt="">',
            MDI_SVG_BASE_URL,
            obj.icon,
        )

    @admin.display(description="Icon", ordering="icon")
    def icon_name(self, obj):
        return obj.get_icon_display()

    @admin.display(description="Site type names and keywords")
    def mapped_site_types(self, obj):
        return ", ".join(obj.site_types) or "—"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        css = {"all": ("admin/web/site_type_icons.css",)}


admin.site.register(InstanceConfiguration)
admin.site.register(MapConfiguration)
admin.site.register(AnalyticsConfiguration)
admin.site.register(MapLayer, MapLayerAdmin)
admin.site.register(ContactInformation, ContactInformationAdmin)
admin.site.register(SiteTypeIcon, SiteTypeIconAdmin)
