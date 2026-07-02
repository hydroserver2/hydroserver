import importlib
import re

import pytest
from django.apps import apps
from django.contrib import admin
from django.conf import settings
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse

from core.sta.models import SiteType
from core.web.admin import SiteTypeIconAdminForm
from core.web.models import (
    SITE_TYPE_ICON_CHOICES,
    InstanceConfiguration,
    SiteTypeIcon,
)


SITE_TYPES = [
    "Conveyance",
    "Stream",
    "Reservoir / Lake",
    "Reservoir Release",
    "Dam / Control Structure",
    "Groundwater Well",
    "Irrigation",
    "Hydropower",
    "Pump Station",
    "Spring",
    "Wetland",
    "Coastal",
    "Snow / Ice",
    "Weather / Atmosphere",
    "Soil",
    "Stormwater",
    "Gaging Station",
    "Water Quality Station",
    "Discrete Sample",
    "Modeled / Calculated",
    "House",
    "Land",
    "Pavement",
    "Site — default fallback",
]


@pytest.mark.django_db
def test_django_and_data_management_app_icon_lists_stay_in_sync():
    django_icons = {icon for icon, _ in SITE_TYPE_ICON_CHOICES}
    seeded_icons = set(SiteTypeIcon.objects.values_list("icon", flat=True))

    data_app_source = (
        settings.BASE_DIR.parent
        / "apps"
        / "data-management"
        / "src"
        / "utils"
        / "siteTypeIcons.ts"
    ).read_text()
    icon_paths_block = data_app_source.split(
        "const iconPaths: Record<string, string> = {", 1
    )[1].split("\n}", 1)[0]
    data_app_icons = {
        quoted_icon or bare_icon
        for quoted_icon, bare_icon in re.findall(
            r"^\s*(?:'([^']+)'|([a-z][\w-]*)):\s*mdi\w+,\s*$",
            icon_paths_block,
            flags=re.MULTILINE,
        )
    }

    assert data_app_icons == django_icons == seeded_icons


@pytest.mark.django_db
def test_default_site_type_icon_mappings_are_available(client):
    response = client.get("/api/data/things/site-type-icons")

    assert response.status_code == 200
    mappings = response.json()
    assert len(mappings) == 24
    assert {
        "icon": "water-well",
        "siteTypes": [
            "Groundwater Well",
            "Observation Well",
            "Ground Water",
            "Groundwater",
            "Borehole",
            "Aquifer",
            "Piezometer",
            "Well",
        ],
    } in mappings
    assert {
        "icon": "gate",
        "siteTypes": [
            "Dam / Control Structure",
            "Dry Dam Release",
            "Dry Dam",
            "Dam",
            "Weir",
            "Sluice",
        ],
    } in mappings
    assert {
        "icon": "hydro-power",
        "siteTypes": ["Hydropower", "Hydro Power", "Power Generation"],
    } in mappings
    assert {
        "icon": "map-marker",
        "siteTypes": [
            "Site — Default Fallback",
            "Monitoring Site",
            "Monitoring Station",
            "Site",
            "Station",
        ],
    } in mappings
    assert {
        "icon": "waves-arrow-right",
        "siteTypes": ["Reservoir Release", "Release", "Outflow", "Spillway"],
    } in mappings


@pytest.mark.django_db
def test_canonical_site_types_are_first_in_default_icon_mappings():
    first_site_types = [
        mapping.site_types[0] for mapping in SiteTypeIcon.objects.order_by("id")
    ]

    assert len(first_site_types) == len(set(first_site_types)) == 24
    assert {site_type.casefold() for site_type in first_site_types} == {
        site_type.casefold() for site_type in SITE_TYPES
    }

    for mapping in SiteTypeIcon.objects.all():
        assert all(keyword == keyword.title() for keyword in mapping.site_types)
        mapping.full_clean()


@pytest.mark.django_db
def test_default_site_type_fixture_contains_canonical_categories():
    SiteType.objects.all().delete()

    call_command("loaddata", "core/sta/fixtures/default_site_types.yaml", verbosity=0)

    assert list(SiteType.objects.order_by("pk").values_list("name", flat=True)) == (
        SITE_TYPES
    )


@pytest.mark.django_db
@override_settings(LOAD_DEFAULT_DATA=True)
def test_new_instance_default_data_loads_canonical_site_types():
    SiteType.objects.all().delete()

    call_command("load_default_data", verbosity=0)

    assert list(SiteType.objects.order_by("pk").values_list("name", flat=True)) == (
        SITE_TYPES
    )


@pytest.mark.django_db
@override_settings(LOAD_DEFAULT_DATA=True)
def test_default_data_does_not_replace_nonempty_site_types():
    SiteType.objects.all().delete()
    SiteType.objects.create(name="Instance-specific site type")

    call_command("load_default_data", verbosity=0)

    assert list(SiteType.objects.values_list("name", flat=True)) == [
        "Instance-specific site type"
    ]


@pytest.mark.django_db
@override_settings(LOAD_DEFAULT_DATA=True)
def test_existing_instance_update_does_not_replace_site_types():
    InstanceConfiguration.get_configuration()
    SiteType.objects.all().delete()
    SiteType.objects.create(name="Instance-specific site type")

    call_command("load_default_data", verbosity=0)

    assert list(SiteType.objects.values_list("name", flat=True)) == [
        "Instance-specific site type"
    ]


@pytest.mark.django_db
def test_site_type_icon_migration_does_not_replace_site_types():
    SiteType.objects.all().delete()
    SiteType.objects.create(name="Instance-specific site type")
    SiteTypeIcon.objects.all().delete()
    migration = importlib.import_module("core.web.migrations.0002_sitetypeicon")

    migration.create_default_site_type_icons(apps, schema_editor=None)

    assert list(SiteType.objects.values_list("name", flat=True)) == [
        "Instance-specific site type"
    ]


@pytest.mark.django_db
def test_site_types_endpoint_remains_a_list_of_names(client):
    response = client.get("/api/data/things/site-types")

    assert response.status_code == 200
    assert all(isinstance(site_type, str) for site_type in response.json())


@pytest.mark.django_db
def test_admin_form_accepts_one_site_type_per_line():
    mapping = SiteTypeIcon.objects.get(icon="beach")
    form = SiteTypeIconAdminForm(
        data={"site_types": "Coastal station\nCustom estuary\n\n"},
        instance=mapping,
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["site_types"] == [
        "Coastal station",
        "Custom estuary",
    ]


@pytest.mark.django_db
def test_site_type_keyword_cannot_map_to_multiple_icons():
    mapping = SiteTypeIcon.objects.get(icon="beach")
    mapping.site_types.append("STREAM!")

    with pytest.raises(ValidationError, match="Already mapped: STREAM!"):
        mapping.full_clean()


def test_site_type_icon_admin_list_is_fixed():
    model_admin = admin.site._registry[SiteTypeIcon]

    assert model_admin.has_add_permission(None) is False
    assert model_admin.has_delete_permission(None) is False


@pytest.mark.django_db
def test_site_type_icon_admin_change_page(admin_client):
    mapping = SiteTypeIcon.objects.get(icon="water")

    response = admin_client.get(
        reverse("admin:web_sitetypeicon_change", args=(mapping.pk,))
    )

    assert response.status_code == 200
    assert b"Site type names and keywords" in response.content
    assert b"admin/web/site_type_icons.css" in response.content
    assert b"site-type-icon-preview" in response.content


@pytest.mark.django_db
def test_admin_can_replace_or_clear_default_site_type_keywords(admin_client):
    mapping = SiteTypeIcon.objects.get(icon="beach")
    change_url = reverse("admin:web_sitetypeicon_change", args=(mapping.pk,))

    response = admin_client.post(
        change_url,
        {"site_types": "Custom coastline\nCustom estuary"},
    )

    assert response.status_code == 302
    mapping.refresh_from_db()
    assert mapping.site_types == ["Custom coastline", "Custom estuary"]
    assert mapping.icon == "beach"

    response = admin_client.post(change_url, {"site_types": ""})

    assert response.status_code == 302
    mapping.refresh_from_db()
    assert mapping.site_types == []
    assert mapping.icon == "beach"
