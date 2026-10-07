import uuid

import pytest

from interfaces.api.schemas.base import accepts_null
from tests.core.iam.factories import RoleFactory, UserFactory, WorkspaceFactory
from tests.core.sta.factories import (
    DatastreamFactory,
    MethodFactory,
    MonitoringSiteFactory,
    UnitFactory,
)
from tests.interfaces.api.helpers import api_operations

pytestmark = pytest.mark.django_db

# 'null' is only a valid query value where the parameter's type declares Literal["null"], and
# there it selects items whose value is null. Everywhere else it's an invalid value, or an
# ordinary string for free-text parameters. Booleans accept only 'true' and 'false' (OGC API -
# Common - Part 1 /req/core/query-param-value-boolean and /req/core/query-param-capitalization).

COLLECTIONS_URL = "/api/ogc/collections"

NULLABLE_PARAMETERS = {
    ("data-product-tasks", "latestRunStatus"),
    ("data-product-tasks", "ratingCurveId"),
    ("datastreams", "status"),
    ("etl-tasks", "latestRunStatus"),
    ("methods", "datastreamId"),
    ("methods", "monitoringSiteId"),
    ("methods", "sensorModel"),
    ("methods", "sensorModelManufacturer"),
    ("methods", "workspaceId"),
    ("monitoring-sites", "adminArea1"),
    ("monitoring-sites", "adminArea2"),
    ("monitoring-sites", "country"),
    ("monitoring-tasks", "latestRunStatus"),
    ("observed-properties", "datastreamId"),
    ("observed-properties", "monitoringSiteId"),
    ("observed-properties", "workspaceId"),
    ("processing-levels", "datastreamId"),
    ("processing-levels", "monitoringSiteId"),
    ("processing-levels", "workspaceId"),
    ("quality-control-histories", "sourceDatastreamId"),
    ("result-qualifiers", "workspaceId"),
    ("roles", "workspaceId"),
    ("units", "datastreamId"),
    ("units", "monitoringSiteId"),
    ("units", "workspaceId"),
}


def _nullable_parameters():
    """Yields (collection id, parameter name) for every query parameter that accepts 'null'."""

    for _, _, prefix, operation in api_operations():
        if not prefix.startswith("collections/"):
            continue

        for model in operation.models:
            if getattr(model, "__ninja_param_source__", None) != "query":
                continue

            for alias, field_path in model.__ninja_flatten_map__.items():
                schema = model
                for name in field_path[:-1]:
                    schema = schema.model_fields[name].annotation
                # The flatten map ends with the parameter's alias, not its field name.
                field = next(
                    field
                    for name, field in schema.model_fields.items()
                    if (field.alias or name) == field_path[-1]
                )
                if accepts_null(field.annotation):
                    yield prefix.removeprefix("collections/"), alias


def test_only_nullable_columns_accept_null():
    assert set(_nullable_parameters()) == NULLABLE_PARAMETERS


def test_null_selects_items_without_a_value(client):
    global_role = RoleFactory(global_role=True)
    RoleFactory()

    response = client.get(f"{COLLECTIONS_URL}/roles/items", {"workspaceId": "null"})

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["data"]}
    assert str(global_role.id) in ids
    assert all(item["workspaceId"] is None for item in response.json()["data"])


def test_null_combines_with_other_values(client):
    user = UserFactory()
    workspace = WorkspaceFactory(owner=user)
    workspace_unit = UnitFactory(workspace=workspace)
    global_unit = UnitFactory(workspace=None)
    other_unit = UnitFactory()
    client.force_login(user)

    response = client.get(
        f"{COLLECTIONS_URL}/units/items?workspaceId={workspace.id}&workspaceId=null&limit=1000"
    )

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["data"]}
    assert {str(workspace_unit.id), str(global_unit.id)} <= ids
    assert str(other_unit.id) not in ids


@pytest.mark.parametrize(
    "collection, parameter, field",
    [
        ("monitoring-sites", "country", "country"),
        ("monitoring-sites", "adminArea1", "admin_area_1"),
        ("methods", "sensorModel", "sensor_model"),
    ],
)
def test_newly_nullable_string_filters_select_null_values(client, collection, parameter, field):
    factory = MonitoringSiteFactory if collection == "monitoring-sites" else MethodFactory
    null_item = factory(**{field: None})
    valued_item = factory(**{field: "US"})
    client.force_login(UserFactory(superuser=True))

    response = client.get(f"{COLLECTIONS_URL}/{collection}/items", {parameter: "null", "limit": 1000})

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["data"]}
    assert str(null_item.id) in ids
    assert str(valued_item.id) not in ids


def test_datastream_status_null_selects_datastreams_without_a_status(client):
    null_datastream = DatastreamFactory(status=None)
    valued_datastream = DatastreamFactory(status="Ongoing")

    response = client.get(f"{COLLECTIONS_URL}/datastreams/items", {"status": "null", "limit": 1000})

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["data"]}
    assert str(null_datastream.id) in ids
    assert str(valued_datastream.id) not in ids


def test_null_matching_is_case_sensitive_for_string_filters(client):
    null_site = MonitoringSiteFactory(admin_area_1=None)
    literal_site = MonitoringSiteFactory(admin_area_1="NULL")

    response = client.get(
        f"{COLLECTIONS_URL}/monitoring-sites/items", {"adminArea1": "NULL", "limit": 1000}
    )

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["data"]}
    assert str(literal_site.id) in ids
    assert str(null_site.id) not in ids


@pytest.mark.parametrize("value", ["NULL", "Null"])
def test_null_matching_is_case_sensitive_for_typed_filters(client, value):
    response = client.get(f"{COLLECTIONS_URL}/roles/items", {"workspaceId": value})

    assert response.status_code == 400


@pytest.mark.parametrize(
    "collection, parameter",
    [
        ("units", "limit"),
        ("units", "offset"),
        ("units", "bbox"),
        ("units", "datetime"),
        ("units", "sortby"),
        ("units", "properties"),
        ("datastreams", "monitoringSiteId"),
        ("datastreams", "isPrivate"),
        ("workspaces", "isAssociated"),
        ("etl-tasks", "workspaceId"),
    ],
)
def test_non_nullable_parameters_reject_null(client, collection, parameter):
    client.force_login(UserFactory())

    response = client.get(f"{COLLECTIONS_URL}/{collection}/items", {parameter: "null"})

    assert response.status_code == 400


def test_free_text_parameters_treat_null_as_a_string(client):
    site = MonitoringSiteFactory(type="null")
    MonitoringSiteFactory(type="Stream")

    response = client.get(f"{COLLECTIONS_URL}/monitoring-sites/items", {"type": "null", "limit": 1000})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(site.id)]


@pytest.mark.parametrize("value, expected", [("true", True), ("false", False)])
def test_boolean_parameters_accept_lowercase_true_and_false(client, value, expected):
    # A site is only private-filtered as private when its workspace is private too.
    private_site = MonitoringSiteFactory(private=True, workspace=WorkspaceFactory(private=True))
    public_site = MonitoringSiteFactory()
    client.force_login(UserFactory(superuser=True))

    response = client.get(f"{COLLECTIONS_URL}/monitoring-sites/items", {"isPrivate": value, "limit": 1000})

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["data"]}
    assert (str(private_site.id) in ids) is expected
    assert (str(public_site.id) in ids) is not expected


@pytest.mark.parametrize("value", ["True", "FALSE", "1", "0", "yes", "no", "t", "f", "on", ""])
@pytest.mark.parametrize(
    "path, parameter",
    [
        ("workspaces/items", "isPrivate"),
        ("workspaces/items", "isAssociated"),
        ("datastreams/items", "isPrivate"),
        ("monitoring-sites/items", "isPrivate"),
    ],
)
def test_boolean_parameters_reject_other_spellings(client, path, parameter, value):
    response = client.get(f"{COLLECTIONS_URL}/{path}", {parameter: value})

    assert response.status_code == 400
    assert response.json()["message"] == "Value error, Boolean query parameters must be 'true' or 'false'"


@pytest.mark.parametrize("value", ["True", "1", "null"])
def test_include_ancestors_rejects_other_spellings(client, value):
    client.force_login(UserFactory())
    history_id = uuid.uuid4()

    response = client.get(
        f"{COLLECTIONS_URL}/quality-control-histories/items/{history_id}/sessions",
        {"includeAncestors": value},
    )

    assert response.status_code == 400
