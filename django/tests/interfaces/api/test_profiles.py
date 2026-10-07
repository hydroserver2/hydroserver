from datetime import timedelta
from urllib.parse import urlsplit

import pytest

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from interfaces.api.formats.profiles import PROFILE_URI_BASE
from tests.core.iam.factories import WorkspaceFactory
from tests.core.sta.factories import (
    DatastreamFactory,
    MonitoringSiteFactory,
    ObservationFactory,
    ResultQualifierFactory,
)
from tests.interfaces.api.helpers import links_by_rel, query_params

pytestmark = pytest.mark.django_db

# Pages of observations can be requested in a profile (OGC API - Common Part 3), by URI: rows or columns of the
# properties of observation records, grouped by datastream. Without one, pages hold records. Profiles apply to
# JSON; other formats ignore them.

OBSERVATIONS_PATH = "/api/ogc/collections/observations/items"
ROW = f"{PROFILE_URI_BASE}/observations/row"
COLUMN = f"{PROFILE_URI_BASE}/observations/column"
OBSERVATION_FIELDS = ["id", "phenomenonTime", "result", "resultQualifiers"]


def _datastream(workspace=None):
    return DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=workspace or WorkspaceFactory()))


def _observations(datastream, count, **kwargs):
    start = timezone.now() - timedelta(days=1)
    return [
        ObservationFactory(
            datastream=datastream, phenomenon_time=start + timedelta(minutes=i), result=float(i), **kwargs
        )
        for i in range(count)
    ]


def _get(client, **params):
    return client.get(OBSERVATIONS_PATH, params)


def _sorted_datastreams(*datastreams):
    return sorted(datastreams, key=lambda datastream: str(datastream.id))


def _records_from_groups(groups):
    """Rebuilds observation records from row or column groups."""

    records = []
    for group in groups:
        shared = {key: group[key] for key in ("datastreamId", "workspaceId") if key in group}
        if "rows" in group:
            records += [{**shared, **dict(zip(group["fields"], row))} for row in group["rows"]]
        else:
            columns = group["columns"]
            length = len(next(iter(columns.values()))) if columns else 0
            records += [{**shared, **{name: values[i] for name, values in columns.items()}} for i in range(length)]

    return records


def test_pages_without_a_profile_hold_records_and_link_no_profile(client):
    datastream = _datastream()
    _observations(datastream, 1)

    response = _get(client, datastreamId=str(datastream.id))

    assert "phenomenonTime" in response.json()["data"][0]
    assert "profile" not in links_by_rel(response)


def test_profile_links_have_no_media_type(client):
    datastream = _datastream()
    _observations(datastream, 1)

    response = _get(client, datastreamId=str(datastream.id), profile=ROW)

    assert links_by_rel(response)["profile"] == {
        "href": ROW,
        "rel": "profile",
        "title": "Observations as rows grouped by datastream",
    }


def test_profiles_are_selected_by_uri(client):
    datastream = _datastream()
    _observations(datastream, 1)

    response = _get(client, datastreamId=str(datastream.id), profile=ROW)

    assert "rows" in response.json()["data"][0]
    assert links_by_rel(response)["profile"]["href"] == ROW


@pytest.mark.parametrize("value", ["row", "column", "record", "https://example.org/unknown"])
def test_values_other_than_profile_uris_fall_back_to_records(client, value):
    datastream = _datastream()
    _observations(datastream, 1)

    response = _get(client, datastreamId=str(datastream.id), profile=value)

    assert response.status_code == 200
    assert "phenomenonTime" in response.json()["data"][0]
    assert "profile" not in links_by_rel(response)


def test_the_first_supported_requested_profile_is_used(client):
    datastream = _datastream()
    _observations(datastream, 1)

    response = _get(client, datastreamId=str(datastream.id), profile=f"https://example.org/unknown,{COLUMN},{ROW}")

    assert "columns" in response.json()["data"][0]


def test_formats_without_profiles_ignore_the_profile_parameter(client):
    datastream = _datastream()
    _observations(datastream, 1)

    response = _get(client, datastreamId=str(datastream.id), profile=ROW, f="geojson")

    assert response.json()["type"] == "FeatureCollection"
    assert "profile" not in links_by_rel(response)


def test_profiles_apply_to_pages_of_observations_not_one_observation(client):
    (observation,) = _observations(_datastream(), 1)

    response = client.get(f"{OBSERVATIONS_PATH}/{observation.id}", {"profile": ROW})

    assert response.status_code == 400
    assert "profile" in response.json()["message"]


def test_page_links_keep_the_profile_and_alternates_drop_it(client):
    datastream = _datastream()
    _observations(datastream, 3)

    response = _get(client, datastreamId=str(datastream.id), profile=COLUMN, limit=2)

    links = links_by_rel(response)
    assert query_params(links["next"]["href"])["profile"] == [COLUMN]
    assert query_params(links["self"]["href"])["profile"] == [COLUMN]
    assert "profile" not in query_params(links["alternate"]["href"])
    assert query_params(links["alternate"]["href"])["f"] == ["geojson"]


@pytest.mark.parametrize("profile", [ROW, COLUMN])
def test_groups_hold_the_shared_properties_of_their_observations(client, profile):
    first, second = _sorted_datastreams(_datastream(), _datastream())
    _observations(first, 2)
    _observations(second, 1)

    response = _get(client, datastreamId=[str(first.id), str(second.id)], profile=profile)

    groups = response.json()["data"]
    assert [(group["datastreamId"], group["workspaceId"]) for group in groups] == [
        (str(first.id), str(first.monitoring_site.workspace_id)),
        (str(second.id), str(second.monitoring_site.workspace_id)),
    ]
    assert all("count" not in group for group in groups)
    if profile == ROW:
        assert groups[0]["fields"] == OBSERVATION_FIELDS
    else:
        assert list(groups[0]["columns"]) == OBSERVATION_FIELDS


@pytest.mark.parametrize("profile", [ROW, COLUMN])
@pytest.mark.parametrize("properties", [None, "result", "id,workspaceId", "datastreamId"])
def test_rows_and_columns_hold_the_same_information_as_records(client, profile, properties):
    workspace = WorkspaceFactory()
    first, second = _sorted_datastreams(_datastream(workspace), _datastream(workspace))
    ResultQualifierFactory(workspace=workspace, name="A")
    _observations(first, 2, result_qualifiers=["A"])
    _observations(second, 1)
    params = {"datastreamId": [str(first.id), str(second.id)], **({"properties": properties} if properties else {})}

    records = _get(client, **params).json()["data"]
    groups = _get(client, **params, profile=profile).json()["data"]

    if profile == COLUMN and properties == "datastreamId":
        # Without any per-observation property, a column group has no column to count observations by.
        assert [group["datastreamId"] for group in groups] == [str(first.id), str(second.id)]
        return

    # datastreamId identifies a group, so groups always hold it.
    expected = [{**record, "datastreamId": record.get("datastreamId", group_id)} for record, group_id in zip(
        records, [str(first.id)] * 2 + [str(second.id)]
    )]
    assert _records_from_groups(groups) == expected


@pytest.mark.parametrize("profile", [ROW, COLUMN])
def test_included_resources_match_records(client, profile):
    workspace = WorkspaceFactory()
    ResultQualifierFactory(workspace=workspace, name="A")
    datastream = _datastream(workspace)
    _observations(datastream, 2, result_qualifiers=["A"])
    params = {"datastreamId": str(datastream.id), "include": "datastream,workspace,resultQualifiers"}

    records = _get(client, **params).json()
    groups = _get(client, **params, profile=profile).json()

    assert groups["included"] == records["included"]
    assert _records_from_groups(groups["data"]) == records["data"]


def test_included_resources_follow_their_page(client):
    first, second = _sorted_datastreams(_datastream(), _datastream())
    _observations(first, 2)
    _observations(second, 2)
    params = {"datastreamId": [str(first.id), str(second.id)], "include": "datastream", "profile": ROW, "limit": 3}

    pages = [_get(client, **params), _get(client, **params, offset=3)]

    assert [[item["id"] for item in page.json()["included"]["datastreams"]] for page in pages] == [
        sorted([str(first.id), str(second.id)]),
        [str(second.id)],
    ]


def test_without_included_resources_only_the_selected_properties_are_read(client):
    datastream = _datastream()
    _observations(datastream, 2)

    with CaptureQueriesContext(connection) as context:
        response = _get(client, datastreamId=str(datastream.id), profile=COLUMN, properties="phenomenonTime,result")

    (group,) = response.json()["data"]
    assert list(group["columns"]) == ["phenomenonTime", "result"]
    assert "workspaceId" not in group
    page_query = next(query["sql"] for query in context.captured_queries if '"phenomenon_time"' in query["sql"]
                      and "LIMIT" in query["sql"])
    selected = page_query.split(" FROM ")[0]
    assert "result_qualifiers" not in selected
    assert "workspace_id" not in selected


def test_column_groups_without_selected_columns_still_page(client):
    datastream = _datastream()
    _observations(datastream, 3)

    response = _get(client, datastreamId=str(datastream.id), profile=COLUMN, properties="datastreamId", limit=2)

    (group,) = response.json()["data"]
    assert group == {"datastreamId": str(datastream.id), "columns": {}}
    assert "next" in links_by_rel(response)


def test_grouped_pages_span_datastreams_and_return_every_observation_once(client):
    first, second = _sorted_datastreams(_datastream(), _datastream())
    expected = {observation.id for observation in [*_observations(first, 3), *_observations(second, 2)]}

    response = _get(client, datastreamId=[str(first.id), str(second.id)], profile=ROW, limit=2)
    pages = [response]
    while "next" in links_by_rel(pages[-1]):
        parts = urlsplit(links_by_rel(pages[-1])["next"]["href"])
        pages.append(client.get(f"{parts.path}?{parts.query}"))

    seen = [row[0] for page in pages for group in page.json()["data"] for row in group["rows"]]
    assert sorted(seen) == sorted(str(observation_id) for observation_id in expected)
    assert [group["datastreamId"] for group in pages[1].json()["data"]] == [str(first.id), str(second.id)]


def test_grouped_profiles_cover_every_viewable_datastream_without_a_filter(client):
    first, second = _datastream(), _datastream()
    _observations(first, 1)
    _observations(second, 1)

    response = _get(client, profile=COLUMN)

    assert {group["datastreamId"] for group in response.json()["data"]} == {str(first.id), str(second.id)}


def test_an_empty_grouped_page_has_no_groups(client):
    response = _get(client, profile=ROW, datastreamId=str(_datastream().id))

    assert response.status_code == 200
    assert response.json()["data"] == []
    assert links_by_rel(response)["profile"]["href"] == ROW


def test_openapi_documents_profile_uris_on_observation_pages(client):
    paths = client.get("/api/ogc/openapi.json").json()["paths"]
    observations = next(item for path, item in paths.items() if path.endswith("/observations/items"))
    observation = next(item for path, item in paths.items() if path.endswith("/observations/items/{observation_id}"))
    units = next(item for path, item in paths.items() if path.endswith("/units/items"))

    (profile,) = [param for param in observations["get"]["parameters"] if param["name"] == "profile"]
    assert profile["style"] == "form" and profile["explode"] is False
    assert profile["schema"]["items"]["enum"] == [ROW, COLUMN]
    for operation in (observation["get"], units["get"]):
        assert "profile" not in {param["name"] for param in operation.get("parameters", [])}


@pytest.mark.parametrize("profile", [ROW, COLUMN])
def test_properties_and_included_resources_combine_like_records(client, profile):
    workspace = WorkspaceFactory()
    datastream = _datastream(workspace)
    _observations(datastream, 2)
    params = {"datastreamId": str(datastream.id), "include": "datastream", "properties": "result,workspaceId"}

    records = _get(client, **params).json()
    groups = _get(client, **params, profile=profile).json()

    assert groups["included"] == records["included"]
    assert _records_from_groups(groups["data"]) == [
        {**record, "datastreamId": str(datastream.id)} for record in records["data"]
    ]


def test_grouped_pages_are_documented_as_paginated_responses(client):
    schema = client.get("/api/ogc/openapi.json").json()
    observations = next(item for path, item in schema["paths"].items() if path.endswith("/observations/items"))
    components = schema["components"]["schemas"]

    content = observations["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert [option["$ref"].rsplit("/", 1)[-1] for option in content["anyOf"]] == [
        "PaginatedResponse_ObservationResponse_",
        "PaginatedResponse_ObservationRowResponse_",
        "PaginatedResponse_ObservationColumnResponse_",
    ]
    assert not {"ObservationFormatResponse", "ObservationColumnarResponse"} & set(components)
    assert "datastreamId" in components["ObservationRowResponse"]["properties"]
    assert "returned" not in components["PaginatedResponse_ObservationRowResponse_"]["properties"]
    assert "rowCount" not in components["ObservationColumnResponse"]["properties"]
