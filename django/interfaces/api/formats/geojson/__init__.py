from typing import Optional

import orjson

from pydantic import BaseModel

from interfaces.api.collections import CollectionDefinition
from interfaces.api.formats.base import DocumentKind, EncodeContext, Format
from interfaces.api.formats.document import ResponseDocument
from interfaces.api.formats.geojson.encoder import geometry_fields, to_geojson


class GeoJSONFormat(Format):
    """GeoJSON, for feature collections (OGC API - Features Core, Requirements Class "GeoJSON")."""

    key = "geojson"
    media_type = "application/geo+json"
    conformance = ("http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson",)

    def required_fields(self, collection: CollectionDefinition) -> frozenset[str]:
        # A feature's id (Req 39B) and its geometry are members of the Feature, not properties.
        return frozenset({"id"}) | geometry_fields(collection)

    def encode(self, document: ResponseDocument, context: EncodeContext) -> bytes:
        return orjson.dumps(to_geojson(document, context.collection), default=str)

    def document_schema(self, collection: CollectionDefinition, kind: DocumentKind) -> Optional[type[BaseModel]]:
        # Imported on use: the schemas use the Link schema, whose module imports the format registry.
        from interfaces.api.formats.geojson.features import feature_collection_schema, feature_schema

        return feature_collection_schema(collection) if kind == "items" else feature_schema(collection)
