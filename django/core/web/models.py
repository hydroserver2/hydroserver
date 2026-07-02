import re

from django.db import models
from django.core.exceptions import ValidationError
from solo.models import SingletonModel


SITE_TYPE_ICON_CHOICES = (
    ("beach", "Beach"),
    ("calculator", "Calculator"),
    ("fountain", "Fountain"),
    ("gate", "Gate"),
    ("gauge", "Gauge"),
    ("grass", "Grass"),
    ("home-outline", "Home"),
    ("hydro-power", "Hydropower"),
    ("image-filter-hdr", "Land"),
    ("map-marker", "Site marker"),
    ("pipe-disconnected", "Disconnected pipe"),
    ("road-variant", "Road"),
    ("snowflake", "Snowflake"),
    ("sprinkler", "Sprinkler"),
    ("terrain", "Terrain"),
    ("test-tube", "Test tube"),
    ("vector-polyline", "Polyline"),
    ("water", "Water"),
    ("water-check", "Water quality"),
    ("water-pump", "Water pump"),
    ("water-well", "Water well"),
    ("waves", "Waves"),
    ("waves-arrow-right", "Waves with right arrow"),
    ("weather-cloudy", "Cloudy weather"),
)


def normalize_site_type_keyword(value):
    return re.sub(r"[\W_]+", " ", value.casefold()).strip()


MAP_LAYER_TYPE_CHOICES = (
    ("basemap", "Basemap"),
    ("overlay", "Overlay"),
)

ELEVATION_SERVICE_CHOICES = (
    ("openElevation", "Open Elevation"),
    ("google", "Google"),
)

GEO_SERVICE_CHOICES = (
    ("nominatim", "Nominatim"),
    ("google", "Google"),
)


class InstanceConfiguration(SingletonModel):
    show_about_information = models.BooleanField(default=False)
    about_page_title = models.CharField(max_length=255, blank=True, null=True)
    about_page_text = models.TextField(blank=True, null=True)
    terms_of_use_link = models.CharField(max_length=255, blank=True, null=True)
    privacy_policy_link = models.CharField(max_length=255, blank=True, null=True)
    copyright = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return "Instance Configuration"

    @classmethod
    def get_configuration(cls):
        if not cls.objects.exists():
            instance_configuration = cls.objects.create()
            MapConfiguration.objects.create(
                instance_configuration=instance_configuration
            )
            AnalyticsConfiguration.objects.create(
                instance_configuration=instance_configuration
            )
            return instance_configuration

        return cls.objects.select_related(
            "map_configuration",
            "analytics_configuration",
            "map_configuration__default_base_layer",
            "map_configuration__default_satellite_layer",
        ).first()

    class Meta:
        verbose_name = "Instance Configuration"
        verbose_name_plural = "Instance Configuration"


class MapConfiguration(SingletonModel):
    instance_configuration = models.OneToOneField(
        InstanceConfiguration,
        on_delete=models.PROTECT,
        related_name="map_configuration",
    )
    default_latitude = models.DecimalField(max_digits=22, decimal_places=16, default=39)
    default_longitude = models.DecimalField(
        max_digits=22, decimal_places=16, default=-100
    )
    default_zoom_level = models.IntegerField(default=4)
    default_base_layer = models.ForeignKey(
        "MapLayer",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="default_base_layer",
    )
    default_satellite_layer = models.ForeignKey(
        "MapLayer",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="default_satellite_layer",
    )
    elevation_service = models.CharField(
        max_length=255, choices=ELEVATION_SERVICE_CHOICES, default="openElevation"
    )
    geo_service = models.CharField(
        max_length=255, choices=GEO_SERVICE_CHOICES, default="nominatim"
    )

    def __str__(self):
        return "Map Configuration"

    class Meta:
        verbose_name = "Map Configuration"
        verbose_name_plural = "Map Configuration"


class AnalyticsConfiguration(SingletonModel):
    instance_configuration = models.OneToOneField(
        InstanceConfiguration,
        on_delete=models.PROTECT,
        related_name="analytics_configuration",
    )
    enable_clarity_analytics = models.BooleanField(default=False)
    clarity_project_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return "Analytics Configuration"

    class Meta:
        verbose_name = "Analytics Configuration"
        verbose_name_plural = "Analytics Configuration"


class ContactInformation(models.Model):
    title = models.CharField(max_length=255, unique=True)
    text = models.TextField(blank=True, null=True)
    action = models.CharField(max_length=255, blank=True, null=True)
    icon = models.CharField(max_length=255, blank=True, null=True)
    link = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Contact Information"
        verbose_name_plural = "Contact Information"


class MapLayer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=255, choices=MAP_LAYER_TYPE_CHOICES)
    priority = models.IntegerField(default=0)
    source = models.CharField(max_length=255)
    attribution = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Map Layer"


class SiteTypeIcon(models.Model):
    icon = models.CharField(
        max_length=50,
        choices=SITE_TYPE_ICON_CHOICES,
        unique=True,
        editable=False,
    )
    site_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Site type names or keywords that should use this icon.",
    )

    def __str__(self):
        return self.get_icon_display()

    def clean(self):
        super().clean()

        if not isinstance(self.site_types, list) or any(
            not isinstance(site_type, str) for site_type in self.site_types
        ):
            raise ValidationError(
                {"site_types": "Site types must be a list of text values."}
            )

        self.site_types = [
            site_type.strip() for site_type in self.site_types if site_type.strip()
        ]
        normalized_site_types = [
            normalize_site_type_keyword(site_type) for site_type in self.site_types
        ]

        if any(not site_type for site_type in normalized_site_types):
            raise ValidationError(
                {
                    "site_types": (
                        "Site type names and keywords must contain at least one "
                        "letter or number."
                    )
                }
            )

        if len(normalized_site_types) != len(set(normalized_site_types)):
            raise ValidationError(
                {"site_types": "Each site type may only appear once for an icon."}
            )

        other_mappings = type(self).objects.exclude(pk=self.pk).values_list(
            "icon", "site_types"
        )
        duplicate_mappings = {
            normalize_site_type_keyword(site_type): icon
            for icon, site_types in other_mappings
            for site_type in site_types
            if isinstance(site_type, str)
        }
        duplicates = [
            site_type
            for site_type in self.site_types
            if normalize_site_type_keyword(site_type) in duplicate_mappings
        ]
        if duplicates:
            raise ValidationError(
                {
                    "site_types": (
                        "A site type or keyword can only map to one icon. "
                        f"Already mapped: {', '.join(duplicates)}."
                    )
                }
            )

    class Meta:
        ordering = ("id",)
        verbose_name = "Site Type Icon"
        verbose_name_plural = "Site Type Icons"
