import pytest

from django.test import override_settings
from django.urls import reverse

from interfaces.api.urls import api

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("proxy_base_url")]

# The landing page links to the API definition, documentation, conformance declaration and
# collections, and /conformance lists the classes the API implements (OGC API - Features Core
# Req 1-6; OGC API - Common Core landing-page and json classes). Links are built from
# PROXY_BASE_URL, not the request's Host, which the test client sends as "testserver".

BASE_URL = "https://hydroserver.example.org"
LANDING_PATH = "/api/ogc/"
CONFORMANCE_PATH = "/api/ogc/conformance"
COMMON_CORE = "http://www.opengis.net/spec/ogcapi-common-1/1.0/conf/core"
COMMON_JSON = "http://www.opengis.net/spec/ogcapi-common-1/1.0/conf/json"
COMMON_LANDING_PAGE = "http://www.opengis.net/spec/ogcapi-common-1/1.0/conf/landing-page"
OGC_CONFORMANCE_REL = "http://www.opengis.net/def/rel/ogc/1.0/conformance"
FEATURES_CORE = "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core"
FEATURES_GEOJSON = "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson"
COMMON_PROFILE_PARAMETER = "http://www.opengis.net/spec/ogcapi-common-3/1.0/conf/profile-parameter"


@pytest.fixture
def proxy_base_url():
    with override_settings(PROXY_BASE_URL=BASE_URL):
        yield


def _links(response):
    return {link["rel"]: link for link in response.json()["links"]}


def test_landing_page_describes_the_api(client):
    response = client.get(LANDING_PATH)

    assert response.status_code == 200
    assert response.json()["title"] == api.title
    assert response.json()["description"] == api.description


def test_landing_page_links(client):
    links = _links(client.get(LANDING_PATH))

    assert {rel: (link["href"], link["type"]) for rel, link in links.items()} == {
        "self": (f"{BASE_URL}/api/ogc/", "application/json"),
        "service-desc": (f"{BASE_URL}/api/ogc/openapi.json", "application/json"),
        "service-doc": (f"{BASE_URL}/api/ogc/docs", "text/html"),
        "conformance": (f"{BASE_URL}/api/ogc/conformance", "application/json"),
        OGC_CONFORMANCE_REL: (f"{BASE_URL}/api/ogc/conformance", "application/json"),
        "data": (f"{BASE_URL}/api/ogc/collections", "application/json"),
    }


@pytest.mark.parametrize(
    "rel", ["self", "service-desc", "service-doc", "conformance", OGC_CONFORMANCE_REL, "data"]
)
def test_landing_page_link_returns_its_declared_media_type(client, rel):
    link = _links(client.get(LANDING_PATH))[rel]

    response = client.get(link["href"].removeprefix(BASE_URL), HTTP_ACCEPT=link["type"])

    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == link["type"]


def test_conformance_declares_the_implemented_classes(client):
    response = client.get(CONFORMANCE_PATH)

    assert response.status_code == 200
    assert response.json() == {
        "conformsTo": [
            COMMON_CORE, COMMON_LANDING_PAGE, FEATURES_CORE, COMMON_JSON, FEATURES_GEOJSON, COMMON_PROFILE_PARAMETER
        ]
    }


@pytest.mark.parametrize("path", [LANDING_PATH, CONFORMANCE_PATH])
def test_capabilities_endpoints_return_json(client, path):
    response = client.get(path, HTTP_ACCEPT="application/json")

    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "application/json"


def test_landing_page_matches_the_common_landing_page_schema(client):
    body = client.get(LANDING_PATH).json()

    assert isinstance(body["links"], list)
    assert all(isinstance(link["href"], str) and isinstance(link["rel"], str) for link in body["links"])


def test_conformance_matches_the_common_conformance_schema(client):
    body = client.get(CONFORMANCE_PATH).json()

    assert isinstance(body["conformsTo"], list)
    assert all(isinstance(uri, str) for uri in body["conformsTo"])


@pytest.mark.parametrize("path", [LANDING_PATH, CONFORMANCE_PATH])
def test_capabilities_endpoints_are_public(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", [LANDING_PATH, CONFORMANCE_PATH])
def test_capabilities_endpoints_reject_unknown_query_parameters(client, path):
    assert client.get(path, {"foo": "bar"}).status_code == 400


def test_api_root_route_name_still_resolves_to_the_landing_page():
    assert reverse("ogc:api-root") == LANDING_PATH


def test_openapi_document_keeps_the_api_path_prefix():
    paths = api.get_openapi_schema(path_prefix=LANDING_PATH)["paths"]

    assert "get" in paths[LANDING_PATH]
    assert "get" in paths[CONFORMANCE_PATH]
    assert "/api/ogc/collections/units/items" in paths


@pytest.mark.parametrize("path", [LANDING_PATH, CONFORMANCE_PATH])
def test_capabilities_endpoints_are_documented_under_capabilities(path):
    paths = api.get_openapi_schema(path_prefix=LANDING_PATH)["paths"]

    assert paths[path]["get"]["tags"] == ["Capabilities"]
