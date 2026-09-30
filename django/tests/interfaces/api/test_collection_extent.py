import pytest

from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import (
    AggregationStatisticFactory,
    DatastreamStatusFactory,
    LinkedResourceTypeFactory,
    MethodFactory,
    MethodTypeFactory,
    MonitoringSiteTypeFactory,
    ObservedPropertyFactory,
    ObservedPropertyTypeFactory,
    ProcessingLevelFactory,
    ResultQualifierFactory,
    SampledMediumFactory,
    UnitFactory,
    UnitTypeFactory,
)

pytestmark = pytest.mark.django_db

# Collections whose items have no geometry: bbox is validated, and every item matches
# (OGC API - Features - Part 1: Core, Req 24C).
NON_SPATIAL_COLLECTIONS = [
    "observed-properties",
    "units",
    "methods",
    "processing-levels",
    "result-qualifiers",
    "monitoring-site-types",
    "linked-resource-types",
    "observed-property-types",
    "unit-types",
    "method-types",
    "sampled-mediums",
    "aggregation-statistics",
    "datastream-statuses",
    "roles",
    "etl-data-connections",
    "etl-mappings",
    "etl-tasks",
    "data-product-rating-curves",
    "data-product-tasks",
    "data-product-transformations",
    "monitoring-rules",
    "monitoring-tasks",
    "quality-control-histories",
]

TEMPORAL_COLLECTIONS = ["observations", "datastreams", "monitoring-sites", "workspaces", "quality-control-histories"]
NON_TEMPORAL_COLLECTIONS = [c for c in NON_SPATIAL_COLLECTIONS if c not in TEMPORAL_COLLECTIONS]
ALL_COLLECTIONS = NON_SPATIAL_COLLECTIONS + ["monitoring-sites", "datastreams", "observations", "workspaces"]

ITEM_FACTORIES = {
    "observed-properties": lambda workspace: ObservedPropertyFactory(workspace=workspace),
    "units": lambda workspace: UnitFactory(workspace=workspace),
    "methods": lambda workspace: MethodFactory(workspace=workspace),
    "processing-levels": lambda workspace: ProcessingLevelFactory(workspace=workspace),
    "result-qualifiers": lambda workspace: ResultQualifierFactory(workspace=workspace),
    "monitoring-site-types": lambda workspace: MonitoringSiteTypeFactory(),
    "linked-resource-types": lambda workspace: LinkedResourceTypeFactory(),
    "observed-property-types": lambda workspace: ObservedPropertyTypeFactory(),
    "unit-types": lambda workspace: UnitTypeFactory(),
    "method-types": lambda workspace: MethodTypeFactory(),
    "sampled-mediums": lambda workspace: SampledMediumFactory(),
    "aggregation-statistics": lambda workspace: AggregationStatisticFactory(),
    "datastream-statuses": lambda workspace: DatastreamStatusFactory(),
}


def _items_url(collection):
    return f"/api/ogc/collections/{collection}/items"


def _without_links(response):
    """The response body without its links, whose self href echoes the request's query string."""

    body = response.json()
    body.pop("links", None)
    return body


@pytest.fixture
def owner_workspace(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)
    return workspace


@pytest.mark.parametrize("collection", NON_SPATIAL_COLLECTIONS)
@pytest.mark.parametrize("bbox", ["-112,40,-111", "-181,40,-111,41", "-112,41,-111,40", "not,a,valid,bbox"])
def test_non_spatial_collection_returns_400_for_invalid_bbox(client, owner_workspace, collection, bbox):
    response = client.get(_items_url(collection), {"bbox": bbox})

    assert response.status_code == 400


@pytest.mark.parametrize("collection", NON_SPATIAL_COLLECTIONS)
def test_non_spatial_collection_ignores_a_valid_bbox(client, owner_workspace, collection):
    unfiltered = client.get(_items_url(collection))
    filtered = client.get(_items_url(collection), {"bbox": "170,-20,-170,-10"})

    assert filtered.status_code == 200
    assert _without_links(filtered) == _without_links(unfiltered)


@pytest.mark.parametrize("collection", ITEM_FACTORIES)
def test_non_spatial_collection_returns_items_for_any_bbox(client, owner_workspace, collection):
    item = ITEM_FACTORIES[collection](owner_workspace)

    response = client.get(_items_url(collection), {"bbox": "0,0,0.001,0.001"})

    assert response.status_code == 200
    assert str(item.id) in [i["id"] for i in response.json()["data"]]


@pytest.mark.parametrize("collection", ALL_COLLECTIONS)
@pytest.mark.parametrize("value", ["2024-01-01", "2024-01-01T00:00:00", "../..", "2024-02-01T00:00:00Z/2024-01-01T00:00:00Z"])
def test_collection_returns_400_for_invalid_datetime(client, owner_workspace, collection, value):
    response = client.get(_items_url(collection), {"datetime": value})

    assert response.status_code == 400


@pytest.mark.parametrize("collection", NON_TEMPORAL_COLLECTIONS)
def test_non_temporal_collection_ignores_a_valid_datetime(client, owner_workspace, collection):
    unfiltered = client.get(_items_url(collection))
    filtered = client.get(_items_url(collection), {"datetime": "1900-01-01T00:00:00Z/1900-01-02T00:00:00Z"})

    assert filtered.status_code == 200
    assert _without_links(filtered) == _without_links(unfiltered)


@pytest.mark.parametrize("collection", ITEM_FACTORIES)
def test_non_temporal_collection_returns_items_for_any_datetime(client, owner_workspace, collection):
    item = ITEM_FACTORIES[collection](owner_workspace)

    response = client.get(_items_url(collection), {"datetime": "1900-01-01T00:00:00Z"})

    assert response.status_code == 200
    assert str(item.id) in [i["id"] for i in response.json()["data"]]
