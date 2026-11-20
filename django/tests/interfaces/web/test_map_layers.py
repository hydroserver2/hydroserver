import pytest
from django.urls import reverse

from core.web.models import MapLayer
from interfaces.web.views import get_app_settings_context

pytestmark = pytest.mark.django_db


def test_existing_map_layers_default_to_hidden_overlays():
    layer = MapLayer.objects.create(
        name="Watersheds",
        type="overlay",
        source="https://example.com/{z}/{x}/{y}.png",
        attribution="Watershed provider",
    )
    layer.refresh_from_db()
    assert not layer.visible_by_default
    assert get_app_settings_context()["mapConfiguration"]["overlayLayers"] == [
        {
            "name": layer.name,
            "source": layer.source,
            "attribution": layer.attribution,
            "priority": 0,
            "visibleByDefault": False,
        }
    ]


@pytest.mark.parametrize("visible", [False, True])
def test_admin_can_configure_overlay_defaults(admin_client, visible):
    data = {
        "name": "Flowlines",
        "type": "overlay",
        "priority": 100,
        "source": "https://example.com/arcgis/rest/services/Flowlines/VectorTileServer?f=json",
        "attribution": "Flowline provider",
    }
    if visible:
        data["visible_by_default"] = "on"
    response = admin_client.post(reverse("admin:web_maplayer_add"), data)
    assert response.status_code == 302
    layer = MapLayer.objects.get(name="Flowlines")
    assert layer.visible_by_default is visible
    settings = get_app_settings_context()["mapConfiguration"]
    assert settings["overlayLayers"] == [
        {
            "name": "Flowlines",
            "source": layer.source,
            "attribution": "Flowline provider",
            "priority": 100,
            "visibleByDefault": visible,
        }
    ]
    assert settings["basemapLayers"] == []


def test_basemap_settings_keep_the_existing_format():
    layer = MapLayer.objects.create(
        name="Basemap",
        type="basemap",
        source="https://example.com/{z}/{x}/{y}.png",
        attribution="Basemap provider",
        visible_by_default=True,
    )
    settings = get_app_settings_context()["mapConfiguration"]
    assert settings["basemapLayers"] == [
        {
            "name": layer.name,
            "source": layer.source,
            "attribution": layer.attribution,
        }
    ]
    assert settings["overlayLayers"] == []
