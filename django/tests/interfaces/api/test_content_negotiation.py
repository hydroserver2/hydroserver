import uuid

import orjson
import pytest

from tests.core.iam.factories import WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory, ObservationFactory, UnitFactory

pytestmark = pytest.mark.django_db

# GET requests to collection items select their format from the f parameter, then the Accept header, then
# the collection's default (OGC API - Features Core Req 7). JSON is the only registered format, so the
# plain_text_format fixture registers a second one to exercise the selection.

UNITS_URL = "/api/ogc/collections/units/items"
OBSERVATIONS_URL = "/api/ogc/collections/observations/items"
OPENAPI_URL = "/api/ogc/openapi.json"
BROWSER_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"


@pytest.fixture
def text_format(plain_text_format):
    return plain_text_format()


def _get(client, url, accept=None, **params):
    headers = {} if accept is None else {"Accept": accept}
    return client.get(url, params, headers=headers)


@pytest.mark.parametrize("accept", [None, "*/*", "", BROWSER_ACCEPT, "application/json"])
def test_items_default_to_json(client, accept):
    UnitFactory(global_=True)

    response = _get(client, UNITS_URL, accept)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json; charset=utf-8"
    assert len(response.json()["data"]) == 1


def test_items_respond_with_vary_accept(client):
    response = client.get(UNITS_URL)

    assert "Accept" in response["Vary"]


def test_f_selects_json(client):
    unit = UnitFactory(global_=True)

    assert _get(client, UNITS_URL, f="json").status_code == 200
    assert _get(client, f"{UNITS_URL}/{unit.id}", f="json").json()["data"]["id"] == str(unit.id)


@pytest.mark.parametrize("f", ["xml", "csv"])
def test_unsupported_f_returns_400(client, f):
    response = _get(client, UNITS_URL, f=f)

    assert response.status_code == 400
    assert response.json()["message"] == f"Unsupported format '{f}'. Allowed: json."


def test_unmatched_accept_returns_406(client):
    response = _get(client, UNITS_URL, "text/csv")

    assert response.status_code == 406
    assert response["Content-Type"] == "application/json; charset=utf-8"
    assert "application/json" in response.json()["message"]
    assert "Accept" in response["Vary"]


def test_f_overrides_accept(client):
    response = _get(client, UNITS_URL, "text/csv", f="json")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json; charset=utf-8"


@pytest.mark.usefixtures("text_format")
def test_accept_selects_a_format(client):
    response = _get(client, UNITS_URL, "text/plain")

    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert "data" in orjson.loads(response.content)


@pytest.mark.usefixtures("text_format")
@pytest.mark.parametrize(
    "accept, media_type",
    [
        ("text/plain;q=0.5, application/json", "application/json"),
        ("application/json;q=0.5, text/plain", "text/plain"),
        ("text/*", "text/plain"),
    ],
)
def test_accept_quality_values_rank_formats(client, accept, media_type):
    response = _get(client, UNITS_URL, accept)

    assert response["Content-Type"] == f"{media_type}; charset=utf-8"


@pytest.mark.usefixtures("text_format")
def test_f_selects_a_format_over_accept(client):
    response = _get(client, UNITS_URL, "application/json", f="text")

    assert response["Content-Type"] == "text/plain; charset=utf-8"


@pytest.mark.usefixtures("text_format")
def test_negotiated_format_keeps_headers_set_by_the_view(client):
    datastream = DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=WorkspaceFactory()))
    ObservationFactory(datastream=datastream)

    response = _get(client, OBSERVATIONS_URL, f="text", datastream_id=str(datastream.id))

    assert "data" in orjson.loads(response.content)
    assert response.has_header("X-Checksum")


@pytest.mark.usefixtures("text_format")
def test_errors_stay_json_whatever_the_format(client):
    response = _get(client, f"{UNITS_URL}/{uuid.uuid4()}", "text/plain")

    assert response.status_code == 404
    assert response["Content-Type"] == "application/json; charset=utf-8"
    assert "message" in response.json()


def test_routes_outside_collection_items_ignore_accept(client):
    response = _get(client, "/api/ogc/collections", "text/csv")

    assert response.status_code == 200
    assert not response.has_header("Vary") or "Accept" not in response["Vary"]


@pytest.mark.parametrize(
    "method, url",
    [
        ("POST", UNITS_URL),
        ("GET", "/api/ogc/collections"),
        ("GET", f"/api/ogc/collections/datastreams/items/{uuid.uuid4()}/linked-resources"),
    ],
)
def test_routes_outside_collection_item_gets_reject_f(client, method, url):
    response = client.generic(method, f"{url}?f=json")

    assert response.status_code == 400
    assert response.json()["message"].startswith("Unknown query parameter(s): f.")


def test_openapi_documents_f_on_collection_item_gets_only(client):
    paths = client.get(OPENAPI_URL).json()["paths"]

    def query_param(path, method):
        return next(
            (param for param in paths[path][method].get("parameters", []) if param["name"] == "f"), None
        )

    items_path = next(path for path in paths if path.endswith("/collections/units/items"))
    item_path = next(path for path in paths if path.endswith("/collections/units/items/{unit_id}"))

    assert query_param(items_path, "get")["schema"] == {"type": "string", "enum": ["json"], "default": "json"}
    assert query_param(item_path, "get") is not None
    assert query_param(items_path, "post") is None
    assert query_param(next(path for path in paths if path.endswith("/collections")), "get") is None
