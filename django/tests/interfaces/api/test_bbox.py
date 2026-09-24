import pytest
from ninja import Query
from ninja.testing import TestClient
from pydantic import ValidationError

from core.sta.models import Datastream, MonitoringSite
from interfaces.api.http import handlers
from interfaces.api.http.api import HydroServerNinjaAPI
from interfaces.api.schemas import BaseQueryParameters, BoundingBox, BoundingBoxQuery, parse_bbox
from interfaces.api.service import APIService
from interfaces.api.urls import api
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory


class _BBoxQueryParameters(BaseQueryParameters):
    bbox: BoundingBoxQuery = Query(None, description="Filter by bounding box.")


_bbox_api = HydroServerNinjaAPI(urls_namespace="bbox-test")
handlers.register(_bbox_api)


@_bbox_api.get("/items")
def _list_items(request, query: Query[_BBoxQueryParameters]):
    bbox = query.bbox
    return None if bbox is None else [bbox.west, bbox.south, bbox.east, bbox.north]


_bbox_client = TestClient(_bbox_api)


# --- parse_bbox ---------------------------------------------------------------------------


def test_parse_bbox_parses_four_numbers():
    assert parse_bbox("-112.5,40,-111,41.25") == BoundingBox(west=-112.5, south=40, east=-111, north=41.25)


def test_parse_bbox_parses_six_numbers_and_drops_the_height_range():
    assert parse_bbox("-112,40,-10,-111,41,2500") == BoundingBox(west=-112, south=40, east=-111, north=41)


def test_parse_bbox_tolerates_whitespace_around_values():
    assert parse_bbox(" -112 , 40 , -111 , 41 ") == BoundingBox(west=-112, south=40, east=-111, north=41)


def test_parse_bbox_accepts_a_sequence_of_values():
    assert parse_bbox([-112, 40, -111, 41]) == BoundingBox(west=-112, south=40, east=-111, north=41)


def test_parse_bbox_accepts_a_box_that_crosses_the_antimeridian():
    bbox = parse_bbox("170,-20,-170,-10")

    assert bbox == BoundingBox(west=170, south=-20, east=-170, north=-10)
    assert bbox.crosses_antimeridian


@pytest.mark.parametrize("value", [None, "null", "NULL"])
def test_parse_bbox_returns_none_for_missing_values(value):
    assert parse_bbox(value) is None


def test_parse_bbox_passes_through_an_existing_bounding_box():
    bbox = BoundingBox(west=-112, south=40, east=-111, north=41)

    assert parse_bbox(bbox) is bbox


@pytest.mark.parametrize(
    "value, message",
    [
        ("-112,40,-111,north", "only numeric values"),
        ("", "only numeric values"),
        ("-112,40,-111,nan", "finite"),
        ("-112,40,-111,inf", "finite"),
        ("-112,40,-111", "4 or 6"),
        ("-112,40,0,-111,41", "4 or 6"),
        ("-112,40,0,-111,41,1,2", "4 or 6"),
        ("-181,40,-111,41", "longitudes"),
        ("-112,40,181,41", "longitudes"),
        ("-112,-91,-111,41", "latitudes"),
        ("-112,40,-111,91", "latitudes"),
        ("-112,41,-111,40", "minimum latitude"),
        ("-112,40,100,-111,41,0", "minimum height"),
    ],
)
def test_parse_bbox_rejects_invalid_values(value, message):
    with pytest.raises(ValueError, match=message):
        parse_bbox(value)


# --- BoundingBox.contains -----------------------------------------------------------------


@pytest.mark.parametrize(
    "longitude, latitude, expected",
    [
        (-111.5, 40.5, True),
        (-112, 40, True),
        (-111, 41, True),
        (-110.9, 40.5, False),
        (-111.5, 41.1, False),
    ],
)
def test_contains_includes_boundaries(longitude, latitude, expected):
    bbox = BoundingBox(west=-112, south=40, east=-111, north=41)

    assert bbox.contains(longitude, latitude) is expected


@pytest.mark.parametrize(
    "longitude, expected",
    [(175, True), (180, True), (-180, True), (-175, True), (0, False), (165, False), (-165, False)],
)
def test_contains_handles_boxes_that_cross_the_antimeridian(longitude, expected):
    bbox = BoundingBox(west=170, south=-20, east=-170, north=-10)

    assert bbox.contains(longitude, -15) is expected


# --- BoundingBoxQuery ---------------------------------------------------------------------


def test_bounding_box_query_parses_the_query_parameter():
    response = _bbox_client.get("/items", query_params={"bbox": "-112,40,-111,41"})

    assert response.status_code == 200
    assert response.json() == [-112, 40, -111, 41]


def test_bounding_box_query_is_optional():
    response = _bbox_client.get("/items")

    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.parametrize("value", ["-112,40,-111", "-112,41,-111,40", "not,a,valid,bbox"])
def test_bounding_box_query_returns_400_for_invalid_values(value):
    response = _bbox_client.get("/items", query_params={"bbox": value})

    assert response.status_code == 400


def test_bounding_box_query_is_declared_per_ogc_core_requirement_23():
    parameters = _bbox_api.get_openapi_schema(path_prefix="")["paths"]["/items"]["get"]["parameters"]
    bbox = next(parameter for parameter in parameters if parameter["name"] == "bbox")

    assert bbox["style"] == "form"
    assert bbox["explode"] is False
    assert bbox["schema"]["type"] == "array"
    assert bbox["schema"]["items"] == {"type": "number"}
    assert bbox["schema"]["oneOf"] == [{"minItems": 4, "maxItems": 4}, {"minItems": 6, "maxItems": 6}]


def test_bounding_box_query_rejects_invalid_values_during_model_validation():
    with pytest.raises(ValidationError):
        _BBoxQueryParameters.model_validate({"bbox": "-112,40,-111"})


def test_bbox_is_declared_on_every_collection_items_list_and_no_nested_list():
    paths = api.get_openapi_schema(path_prefix="/api/ogc/")["paths"]

    def declares_bbox(path):
        return any(p["name"] == "bbox" for p in paths[path]["get"].get("parameters", []))

    items_lists = [path for path in paths if path.endswith("/items") and "get" in paths[path]]
    nested_lists = [
        path
        for path in paths
        if "/items/{" in path and not path.rsplit("/", 1)[-1].startswith("{") and "get" in paths[path]
        and not path.endswith("/csv")
    ]

    assert len(items_lists) == 27
    assert [path for path in items_lists if not declares_bbox(path)] == []
    assert nested_lists and [path for path in nested_lists if declares_bbox(path)] == []


# --- APIService.apply_bbox ----------------------------------------------------------------


@pytest.mark.django_db
def test_apply_bbox_returns_the_queryset_unfiltered_without_a_box():
    MonitoringSiteFactory.create_batch(2)

    assert APIService.apply_bbox(MonitoringSite.objects.all(), None).count() == 2


@pytest.mark.django_db
def test_apply_bbox_matches_points_inside_the_box_including_boundaries():
    inside = MonitoringSiteFactory(longitude=-111.5, latitude=40.5)
    on_corner = MonitoringSiteFactory(longitude=-112, latitude=40)
    MonitoringSiteFactory(longitude=-110, latitude=40.5)
    MonitoringSiteFactory(longitude=-111.5, latitude=42)

    bbox = BoundingBox(west=-112, south=40, east=-111, north=41)
    matched = set(APIService.apply_bbox(MonitoringSite.objects.all(), bbox).values_list("id", flat=True))

    assert matched == {inside.id, on_corner.id}


@pytest.mark.django_db
def test_apply_bbox_matches_both_sides_of_the_antimeridian():
    east_of_west_edge = MonitoringSiteFactory(longitude=175, latitude=-15)
    west_of_east_edge = MonitoringSiteFactory(longitude=-175, latitude=-15)
    MonitoringSiteFactory(longitude=0, latitude=-15)
    MonitoringSiteFactory(longitude=175, latitude=-30)

    bbox = BoundingBox(west=170, south=-20, east=-170, north=-10)
    matched = set(APIService.apply_bbox(MonitoringSite.objects.all(), bbox).values_list("id", flat=True))

    assert matched == {east_of_west_edge.id, west_of_east_edge.id}


@pytest.mark.django_db
def test_apply_bbox_supports_related_field_paths():
    inside = DatastreamFactory(monitoring_site=MonitoringSiteFactory(longitude=-111.5, latitude=40.5))
    DatastreamFactory(monitoring_site=MonitoringSiteFactory(longitude=-100, latitude=40.5))

    bbox = BoundingBox(west=-112, south=40, east=-111, north=41)
    queryset = APIService.apply_bbox(
        Datastream.objects.all(), bbox, "monitoring_site__latitude", "monitoring_site__longitude"
    )

    assert list(queryset.values_list("id", flat=True)) == [inside.id]
