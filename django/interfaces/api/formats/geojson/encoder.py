from typing import Optional

from django.http import HttpRequest

from interfaces.api.collections import CollectionDefinition
from interfaces.api.formats.document import ResponseDocument
from interfaces.api.geometry import NO_GEOMETRY, ResolvedGeometry


def geometry_fields(collection: Optional[CollectionDefinition]) -> frozenset[str]:
    """The item fields a collection's features need to resolve their geometry."""

    source = collection.feature.geometry if collection is not None and collection.feature else None

    return frozenset(source.fields) if source is not None else frozenset()


def requested_properties(request: HttpRequest) -> Optional[set[str]]:
    """The properties named by the request's properties parameter, or None without one."""

    requested = {name.strip() for value in request.GET.getlist("properties") for name in value.split(",")} - {""}

    return requested or None


def omitted_fields(collection: CollectionDefinition, request: HttpRequest) -> set[str]:
    """
    The item fields left out of a feature's properties: the id, which becomes the feature id, fields holding the
    geometry, and fields the geometry was resolved from that the properties parameter didn't select.
    """

    source = collection.feature.geometry if collection.feature else None
    if source is None:
        return {"id"}

    requested = requested_properties(request)
    unrequested = set(source.fields) - requested if requested is not None else set()

    return {"id", *source.geometry_fields, *unrequested}


def to_feature(item: dict, omitted: set[str], resolved: ResolvedGeometry) -> dict:
    """Converts an item into a GeoJSON Feature, leaving the omitted fields out of its properties."""

    properties = {key: value for key, value in item.items() if key not in omitted}

    feature = {"type": "Feature", "id": str(item["id"]), "geometry": resolved.geometry, "properties": properties}
    if resolved.bbox is not None:
        feature["bbox"] = resolved.bbox

    return feature


def to_geojson(document: ResponseDocument, collection: CollectionDefinition, request: HttpRequest) -> dict:
    """
    Converts a response document of a collection's items into a GeoJSON FeatureCollection, or of one item into a
    GeoJSON Feature, with links and included resources as foreign members (OGC API - Features Core Req 39).
    """

    items = [document.items] if document.is_item else document.items
    source = collection.feature.geometry if collection.feature else None
    geometries = source.resolve(items, request) if source is not None and items else [NO_GEOMETRY] * len(items)
    omitted = omitted_fields(collection, request)
    features = [to_feature(item, omitted, resolved) for item, resolved in zip(items, geometries)]

    foreign_members = {"links": document.links}
    if document.included:
        foreign_members["included"] = document.included

    if document.is_item:
        return {**features[0], **foreign_members}

    feature_collection = {"type": "FeatureCollection", "features": features}
    if document.number_matched is not None:
        feature_collection["numberMatched"] = document.number_matched
    feature_collection["numberReturned"] = len(document.items)

    return {**feature_collection, **foreign_members}
