import re

import pytest
from django.contrib import admin
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse

from core.web.admin import SiteTypeIconAdminForm
from core.web.models import SITE_TYPE_ICON_CHOICES, SiteTypeIcon


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
            "groundwater well",
            "observation well",
            "ground water",
            "groundwater",
            "borehole",
            "aquifer",
            "piezometer",
            "well",
        ],
    } in mappings
    assert {
        "icon": "gate",
        "siteTypes": ["dry dam release", "dry dam", "dam", "weir", "sluice"],
    } in mappings
    assert {
        "icon": "hydro-power",
        "siteTypes": ["hydropower", "hydro power", "power generation"],
    } in mappings
    assert {
        "icon": "map-marker-radius-outline",
        "siteTypes": ["monitoring site", "monitoring station", "site", "station"],
    } in mappings
    assert {
        "icon": "waves-arrow-right",
        "siteTypes": ["reservoir release", "release", "outflow", "spillway"],
    } in mappings


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
