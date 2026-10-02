from django.utils.module_loading import import_string
from pydantic import BaseModel

from interfaces.api.collections import CollectionDefinition, get_collection
from interfaces.api.formats.geojson.schemas import GeoJSONFeatureCollection, GeoJSONFeatureDocument

# Models of the GeoJSON responses of feature collections. They document the responses in the OpenAPI document;
# the responses themselves are converted from the validated JSON response documents (encoder.py), not
# validated again.


def feature_properties_schema(collection_id: str) -> type[BaseModel]:
    """The schema of the properties of a collection's features (FeatureType.properties_schema)."""

    return import_string(get_collection(collection_id).feature.properties_schema)


def feature_collection_schema(collection: CollectionDefinition) -> type[BaseModel]:
    return GeoJSONFeatureCollection[feature_properties_schema(collection.id)]


def feature_schema(collection: CollectionDefinition) -> type[BaseModel]:
    return GeoJSONFeatureDocument[feature_properties_schema(collection.id)]
