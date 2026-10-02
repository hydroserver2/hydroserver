from typing import Optional

from interfaces.api.collections import CollectionDefinition
from interfaces.api.formats.document import ResponseDocument


def geometry_fields(collection: Optional[CollectionDefinition]) -> frozenset[str]:
    """The item fields a collection's features build their geometry from."""

    geometry = collection.feature.geometry if collection is not None and collection.feature else None

    return frozenset(geometry.fields) if geometry is not None else frozenset()


def to_feature(item: dict, collection: CollectionDefinition) -> dict:
    """
    Converts an item into a GeoJSON Feature. The id becomes the feature id and the geometry fields become its
    geometry, so neither is repeated in its properties.
    """

    properties = dict(item)
    feature_id = properties.pop("id")
    geometry = None
    point = collection.feature.geometry if collection.feature else None

    if point is not None:
        longitude = properties.pop(point.longitude, None)
        latitude = properties.pop(point.latitude, None)

        # Points are 2D: a third coordinate is ellipsoidal height in CRS84 (OGC API - Features Core Req 10), and
        # elevations are relative to a vertical datum, so they stay in the properties.
        if longitude is not None and latitude is not None:
            geometry = {"type": "Point", "coordinates": [longitude, latitude]}

    return {"type": "Feature", "id": str(feature_id), "geometry": geometry, "properties": properties}


def to_geojson(document: ResponseDocument, collection: CollectionDefinition) -> dict:
    """
    Converts a response document of a collection's items into a GeoJSON FeatureCollection, or of one item into a
    GeoJSON Feature, with links and included resources as foreign members (OGC API - Features Core Req 39).
    """

    foreign_members = {"links": document.links}
    if document.included:
        foreign_members["included"] = document.included

    if document.is_item:
        return {**to_feature(document.items, collection), **foreign_members}

    feature_collection = {
        "type": "FeatureCollection",
        "features": [to_feature(item, collection) for item in document.items],
    }
    if document.number_matched is not None:
        feature_collection["numberMatched"] = document.number_matched
    feature_collection["numberReturned"] = len(document.items)

    return {**feature_collection, **foreign_members}
