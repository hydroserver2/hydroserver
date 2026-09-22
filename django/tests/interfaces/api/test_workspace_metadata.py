"""Shared metadata field rules and the observation qualifier wire contract."""

import pytest

from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, ResultQualifierFactory

pytestmark = pytest.mark.django_db

METADATA = [
    ("methods", {"type": "Instrument Deployment", "description": "Comments"}),
    ("observed-properties", {"type": "Hydrology", "description": "Comments"}),
    ("processing-levels", {"description": "Comments"}),
    ("result-qualifiers", {"description": "Comments"}),
    ("units", {"symbol": "m", "type": "Length"}),
]


@pytest.fixture
def owner_workspace(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)
    return workspace


@pytest.mark.parametrize("resource,fields", METADATA)
def test_metadata_optional_fields_and_limits(client, owner_workspace, resource, fields):
    url = f"/api/data/{resource}"
    body = {**fields, "name": "N" * 255, "workspaceId": str(owner_workspace.id)}
    response = client.post(url, data=body, content_type="application/json")
    assert response.status_code == 201, response.content
    detail_url = f"{url}/{response.json()['id']}"
    data = client.get(detail_url).json()["data"]
    if resource == "result-qualifiers":
        assert "definition" not in data
    else:
        assert data["definition"] is None
    if resource == "units":
        assert "code" not in data and "description" not in data
    else:
        assert data["code"] is None

    definition = "https://example.com/" + "a" * (2000 - len("https://example.com/"))
    changes = {} if resource == "result-qualifiers" else {"definition": definition}
    if resource != "units":
        changes.update(code="C" * 255, description="D" * 5000)
    response = client.patch(detail_url, data=changes, content_type="application/json")
    assert response.status_code == 204, response.content
    if resource != "result-qualifiers":
        assert client.get(detail_url).json()["data"]["definition"] == definition

    invalid = [{"name": "N" * 256}, {"name": ""}]
    if resource != "result-qualifiers":
        invalid.extend([{"definition": "not a URL"}, {"definition": definition + "x"}])
    if resource != "units":
        invalid.extend([{"code": "C" * 256}, {"description": ""}, {"description": None}])
    for change in invalid:
        response = client.patch(detail_url, data=change, content_type="application/json")
        assert response.status_code == 400, (change, response.content)

    cleared = {} if resource == "result-qualifiers" else {"definition": None}
    if resource != "units":
        cleared["code"] = None
    assert client.patch(detail_url, data=cleared, content_type="application/json").status_code == 204


@pytest.mark.parametrize("resource,fields", METADATA)
def test_metadata_requires_name_and_description(client, owner_workspace, resource, fields):
    body = {**fields, "workspaceId": str(owner_workspace.id)}
    assert client.post(f"/api/data/{resource}", data=body, content_type="application/json").status_code == 400
    if resource != "units":
        body["name"] = "Name"
        del body["description"]
        assert client.post(f"/api/data/{resource}", data=body, content_type="application/json").status_code == 400


@pytest.mark.parametrize("global_", [False, True])
def test_qualifier_names_are_unique_within_scope(client, owner_workspace, global_):
    scope = None if global_ else owner_workspace
    first = ResultQualifierFactory(workspace=scope, name="Estimated", code="EXTERNAL")
    second = ResultQualifierFactory(workspace=scope, name="Provisional", code="EXTERNAL")
    # The database enforces name uniqueness, including for system metadata.
    from django.core.exceptions import ValidationError
    second.name = first.name
    with pytest.raises(ValidationError):
        second.full_clean()
    ResultQualifierFactory(name=first.name)  # Another workspace is independent.


def test_qualifier_name_search_sort_and_projection(client, owner_workspace):
    qualifier = ResultQualifierFactory(workspace=owner_workspace, name="Estimated", code="EXT")
    response = client.get("/api/data/result-qualifiers", {
        "q": "Estimated", "sortby": "name", "properties": "id,name",
    })
    assert response.status_code == 200
    assert response.json()["data"] == [{"id": str(qualifier.id), "name": "Estimated"}]
    qualifier.name = "Provisional"
    qualifier.save()
    assert client.get("/api/data/result-qualifiers", {"q": "Provisional"}).json()["data"][0]["name"] == "Provisional"
    assert client.get("/api/data/result-qualifiers", {"q": "Estimated"}).json()["data"] == []


@pytest.mark.parametrize("global_", [False, True])
def test_observation_codes_use_qualifier_names(client, owner_workspace, global_):
    datastream = DatastreamFactory(monitoring_site__workspace=owner_workspace)
    qualifier = ResultQualifierFactory(
        workspace=None if global_ else owner_workspace,
        name="Estimated", code="EXTERNAL-ID",
    )
    body = {
        "datastreamId": str(datastream.id), "phenomenonTime": "2026-01-01T00:00:00Z",
        "result": 1.0, "resultQualifierCodes": [qualifier.name],
    }
    response = client.post("/api/data/observations", data=body, content_type="application/json")
    assert response.status_code == 201, response.content
    response = client.get("/api/data/observations", {"datastream_id": str(datastream.id), "result_qualifier_code": qualifier.name})
    assert response.status_code == 200
    assert response.json()["data"][0]["resultQualifierCodes"] == [qualifier.name]
    body.update(phenomenonTime="2026-01-02T00:00:00Z", resultQualifierCodes=[qualifier.code])
    assert client.post("/api/data/observations", data=body, content_type="application/json").status_code == 400


def test_visualization_allows_observed_property_without_code(client, owner_workspace):
    datastream = DatastreamFactory(
        monitoring_site__workspace=owner_workspace, observed_property__code=None,
        processing_level__code=None,
    )
    response = client.get("/api/data/datastreams/visualization-bootstrap")
    assert response.status_code == 200, response.content
    properties = response.json()["observedProperties"]
    assert next(p for p in properties if p["id"] == str(datastream.observed_property_id))["code"] is None


def test_bulk_observation_codes_use_qualifier_names(client, owner_workspace):
    datastream = DatastreamFactory(monitoring_site__workspace=owner_workspace)
    qualifier = ResultQualifierFactory(workspace=owner_workspace, name="Estimated", code=None)
    body = {
        "datastreamId": str(datastream.id),
        "fields": ["phenomenonTime", "result", "resultQualifierCodes"],
        "data": [["2026-01-01T00:00:00Z", 1.0, [qualifier.name]]],
    }
    response = client.post("/api/data/observations/bulk-create?mode=insert", data=body, content_type="application/json")
    assert response.status_code == 201, response.content
    assert datastream.observation_set.get().result_qualifiers == [qualifier.name]
