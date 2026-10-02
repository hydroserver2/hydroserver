from typing import Optional

from django.http import HttpRequest

from interfaces.api.collections import CollectionDefinition
from interfaces.api.formats.document import ResponseDocument
from interfaces.api.geometry import NO_GEOMETRY, ResolvedGeometry


def geometry_fields(collection: Optional[CollectionDefinition]) -> frozenset[str]:
    """The item fields a collection's features need to resolve their geometry."""

    source = collection.feature.geometry if collection is not None and collection.feature else None

    return frozenset(source.fields) if source is not None else frozenset()


def to_feature(item: dict, collection: CollectionDefinition, resolved: ResolvedGeometry) -> dict:
    """
    Converts an item into a GeoJSON Feature. The id becomes the feature id, and fields holding the geometry aren't
    repeated as properties.
    """

    source = collection.feature.geometry if collection.feature else None
    omitted = {"id", *(source.geometry_fields if source is not None else ())}
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
    features = [to_feature(item, collection, resolved) for item, resolved in zip(items, geometries)]

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
