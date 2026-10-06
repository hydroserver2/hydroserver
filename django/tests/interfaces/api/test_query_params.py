import re
import uuid

import pytest

from interfaces.api.http.query_params import declared_query_params
from interfaces.api.urls import api
from tests.core.sta.factories import DatastreamFactory, ObservationFactory

pytestmark = pytest.mark.django_db

# Query parameters an operation doesn't declare get a 400 (OGC API - Features Core Req 8).

API_PREFIX = "/api/ogc/"
UNITS_URL = "/api/ogc/collections/units/items"


def _operations():
    """Yields (method, OpenAPI-style path, operation) for every operation in the API."""

    for bound_router in api._get_bound_routers():
        for path, path_view in bound_router.path_operations.items():
            route = "/".join(part.strip("/") for part in (bound_router.prefix, path) if part.strip("/"))
            for operation in path_view.operations:
                for method in operation.methods:
                    yield method, f"{API_PREFIX}{route}", operation


OPERATIONS = list(_operations())


@pytest.mark.parametrize(
    "method, path, operation",
    OPERATIONS,
    ids=[f"{method} {path.removeprefix(API_PREFIX)}" for method, path, _ in OPERATIONS],
)
def test_every_operation_rejects_an_unknown_query_parameter(client, method, path, operation):
    url = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)

    response = client.generic(method, f"{url}?notAParameter=1")

    assert response.status_code == 400
    assert "notAParameter" in response.json()["message"]


def test_declared_query_parameters_match_the_openapi_document():
    paths = api.get_openapi_schema(path_prefix=API_PREFIX)["paths"]

    for method, path, operation in OPERATIONS:
        documented = {
            parameter["name"]
            for parameter in paths[path][method.lower()].get("parameters", [])
            if parameter["in"] == "query"
        }

        assert declared_query_params(operation) == documented, f"{method} {path}"


def test_unknown_parameter_message_lists_the_allowed_parameters(client):
    response = client.get(UNITS_URL, {"sortBy": "name"})

    assert response.status_code == 400
    assert response.json()["message"].startswith("Unknown query parameter(s): sortBy. Allowed: ")
    assert "sortby" in response.json()["message"]


def test_parameter_names_are_case_sensitive(client):
    response = client.get(UNITS_URL, {"Limit": 5})

    assert response.status_code == 400


def test_unknown_parameter_without_a_value_is_rejected(client):
    response = client.get(f"{UNITS_URL}?foo")

    assert response.status_code == 400


def test_all_unknown_parameters_are_reported(client):
    response = client.get(UNITS_URL, {"foo": 1, "bar": 2, "limit": 5})

    assert response.status_code == 400
    assert "bar, foo." in response.json()["message"]


def test_declared_parameters_are_accepted(client):
    response = client.get(UNITS_URL, {"limit": 5, "offset": 0, "sortby": "-name,+symbol", "properties": "name"})

    assert response.status_code == 200


def test_repeated_declared_parameters_are_accepted(client):
    response = client.get(f"{UNITS_URL}?properties=name&properties=symbol")

    assert response.status_code == 200


def test_aliased_parameters_are_accepted(client):
    datastream = DatastreamFactory()
    ObservationFactory(datastream=datastream)

    response = client.get(
        "/api/ogc/collections/observations/items",
        {"datastream_id": str(datastream.id), "format": "row", "result_qualifier_code": "A"},
    )

    assert response.status_code == 200


def test_invalid_values_of_declared_parameters_keep_their_validation_error(client):
    response = client.get(UNITS_URL, {"limit": "abc"})

    assert response.status_code == 400
    assert response.json()["message"] == "Input should be a valid integer, unable to parse string as an integer"


def test_operation_without_query_parameters_rejects_any(client):
    response = client.get("/api/ogc/collections/monitoring-sites/site-type-icons", {"foo": 1})

    assert response.status_code == 400
    assert response.json()["message"] == "Unknown query parameter(s): foo. This operation accepts none."


def test_operation_without_query_parameters_accepts_none(client):
    response = client.get("/api/ogc/collections/monitoring-sites/site-type-icons")

    assert response.status_code == 200
