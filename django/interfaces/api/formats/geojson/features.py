from django.utils.module_loading import import_string
from pydantic import BaseModel

from interfaces.api.collections import CollectionDefinition
from interfaces.api.formats.geojson.schemas import GeoJSONFeatureCollection, GeoJSONFeatureDocument


def feature_properties_schema(collection: CollectionDefinition) -> type[BaseModel]:
    """The schema of the properties of a collection's features (FeatureType.properties_schema)."""

    return import_string(collection.feature.properties_schema)


def feature_collection_schema(collection: CollectionDefinition) -> type[BaseModel]:
    """Generates the schema for a GeoJSON Feature Collection based on the given collection definition."""

    return GeoJSONFeatureCollection[feature_properties_schema(collection)]


def feature_schema(collection: CollectionDefinition) -> type[BaseModel]:
    """Generates the schema for a GeoJSON Feature Document based on the given collection definition."""

    return GeoJSONFeatureDocument[feature_properties_schema(collection)]
