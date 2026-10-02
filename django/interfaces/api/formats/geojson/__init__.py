from typing import Optional

from pydantic import BaseModel

from interfaces.api.collections import CollectionDefinition
from interfaces.api.formats.base import DocumentKind, EncodeContext, Format
from interfaces.api.formats.document import ResponseDocument
from interfaces.api.formats.geojson.encoder import geometry_fields, to_geojson
from interfaces.api.http.renderer import ORJSONRenderer


class GeoJSONFormat(Format):
    """GeoJSON, for feature collections."""

    key = "geojson"
    media_type = "application/geo+json"
    conformance = ("http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson",)

    def required_fields(self, collection: CollectionDefinition) -> frozenset[str]:
        return frozenset({"id"}) | geometry_fields(collection)

    _renderer = ORJSONRenderer()

    def encode(self, document: ResponseDocument, context: EncodeContext) -> bytes:
        return self._renderer.render(
            context.request, to_geojson(document, context.collection), response_status=context.status
        )

    def document_schema(self, collection: CollectionDefinition, kind: DocumentKind) -> Optional[type[BaseModel]]:
        from interfaces.api.formats.geojson.features import feature_collection_schema, feature_schema

        return feature_collection_schema(collection) if kind == "items" else feature_schema(collection)
