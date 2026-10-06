import pytest

from tests.core.iam.factories import UserFactory
from tests.core.sta.factories import MonitoringSiteFactory, UnitFactory

pytestmark = pytest.mark.django_db

# Query parameter encoding rules from OGC API - Common - Part 1: Core (conformance class
# http://www.opengis.net/spec/ogcapi-common-1/1.0/conf/core). The comma-delimited list parameters
# are properties, include, sortby and bbox; parameters repeated as name=value pairs are exempt.

UNITS_PATH = "/api/ogc/collections/units/items"
SITES_PATH = "/api/ogc/collections/monitoring-sites/items"


@pytest.fixture
def units():
    return [UnitFactory(global_=True, name=name, symbol=symbol) for name, symbol in [("B", "b"), ("A", "a")]]


@pytest.fixture
def site():
    return MonitoringSiteFactory(latitude=40.5, longitude=-111.5)


# --- Req 6 tolerance: an escaped comma separates list items -------------------------------------
#
# Req 6 reads %2C as part of an item, but Python requests and browser URLSearchParams always
# percent-encode commas, so standard clients send lists as a%2Cb. No valid value of these
# parameters contains a comma, so the API treats %2C as a separator, as allowed by
# /per/core/query-param-value-tolerance.


def test_escaped_comma_separates_properties(client, units):
    response = client.get(f"{UNITS_PATH}?properties=name%2Csymbol")

    assert response.status_code == 200
    assert all(set(unit) == {"name", "symbol"} for unit in response.json()["data"])


def test_escaped_comma_separates_sortby_fields(client, units):
    response = client.get(f"{UNITS_PATH}?sortby=name%2C-symbol")

    assert response.status_code == 200
    assert [unit["name"] for unit in response.json()["data"]] == ["A", "B"]


def test_escaped_comma_separates_include_relations(client, units):
    response = client.get(f"{UNITS_PATH}?include=workspace%2Ctype")

    assert response.status_code == 200


def test_escaped_comma_separates_bbox_values(client, site):
    response = client.get(f"{SITES_PATH}?bbox=-112%2C40%2C-111%2C41")

    assert response.status_code == 200
    assert [s["id"] for s in response.json()["data"]] == [str(site.id)]


def test_unescaped_comma_separates_list_items(client, units):
    response = client.get(f"{UNITS_PATH}?properties=name,symbol")

    assert response.status_code == 200
    assert all(set(unit) == {"name", "symbol"} for unit in response.json()["data"])


def test_repeated_list_parameters_combine_their_items(client, units):
    response = client.get(f"{UNITS_PATH}?properties=name&properties=symbol")

    assert response.status_code == 200
    assert all(set(unit) == {"name", "symbol"} for unit in response.json()["data"])


def test_unescaped_comma_separates_bbox_values(client, site):
    response = client.get(f"{SITES_PATH}?bbox=-112,40,-111,41")

    assert response.status_code == 200
    assert [s["id"] for s in response.json()["data"]] == [str(site.id)]


# --- Req 7: an empty value is an empty list ------------------------------------------------


@pytest.mark.parametrize(
    "path, parameter",
    [(UNITS_PATH, "properties"), (UNITS_PATH, "include"), (UNITS_PATH, "sortby"), (SITES_PATH, "bbox")],
)
def test_empty_list_parameter_behaves_as_if_omitted(client, units, site, path, parameter):
    omitted = client.get(path)

    response = client.get(f"{path}?{parameter}=")

    assert response.status_code == 200
    assert response.json()["data"] == omitted.json()["data"]


# --- Req 8: booleans ---------------------------------------------------------------------


@pytest.mark.parametrize("value, expected", [("true", True), ("false", False)])
def test_boolean_values(client, value, expected):
    owner = UserFactory()
    MonitoringSiteFactory(workspace__owner=owner, workspace__is_private=True, is_private=True)
    MonitoringSiteFactory(workspace__owner=owner, is_private=False)
    client.force_login(owner)

    response = client.get(SITES_PATH, {"isPrivate": value})

    assert response.status_code == 200
    assert [s["isPrivate"] for s in response.json()["data"]] == [expected]


# --- Reqs 9-11: integers, decimals and doubles ------------------------------------------------


def test_integer_with_leading_zeros(client, units):
    response = client.get(UNITS_PATH, {"limit": "001"})

    assert response.status_code == 200
    assert response.json()["meta"]["limit"] == 1


@pytest.mark.parametrize(
    "bbox",
    ["-112.500,040.00,-111.0,41", "-1.12e2,4.0e1,-1.11e2,41", "-112,40,-111,41.250"],
)
def test_bbox_accepts_decimal_and_exponent_forms(client, site, bbox):
    response = client.get(SITES_PATH, {"bbox": bbox})

    assert response.status_code == 200
    assert [s["id"] for s in response.json()["data"]] == [str(site.id)]


# --- Tolerance kept for sortby: an unencoded '+' arrives as a space --------------------------------


def test_sortby_unencoded_plus_still_sorts_ascending(client, units):
    response = client.get(f"{UNITS_PATH}?sortby=+name")

    assert response.status_code == 200
    names = [unit["name"] for unit in response.json()["data"]]
    assert names == sorted(names)
