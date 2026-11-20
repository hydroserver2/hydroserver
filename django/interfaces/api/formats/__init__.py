from interfaces.api.collections import CollectionDefinition
from interfaces.api.formats.base import DocumentKind, EncodeContext, Format
from interfaces.api.formats.document import ResponseDocument
from interfaces.api.formats.geojson import GeoJSONFormat
from interfaces.api.formats.json import JSONFormat

# The formats collections can serve their items in, by the f parameter value that selects them.
FORMATS: dict[str, Format] = {fmt.key: fmt for fmt in (JSONFormat(), GeoJSONFormat())}


def get_format(key: str) -> Format:
    return FORMATS[key]


def collection_formats(collection: CollectionDefinition) -> list[Format]:
    """The collection's formats, its default first."""

    return [FORMATS[key] for key in collection.formats]


def formats_conformance(collections) -> list[str]:
    """The conformance classes of the formats the collections serve, in registry order."""

    used = {key for collection in collections for key in collection.formats}

    return [uri for key, fmt in FORMATS.items() if key in used for uri in fmt.conformance]
