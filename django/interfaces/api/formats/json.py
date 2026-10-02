from typing import Any

from interfaces.api.formats.base import EncodeContext, Format
from interfaces.api.http.renderer import ORJSONRenderer


class JSONFormat(Format):
    """The default format: the JSON response documents the views' response schemas describe."""

    key = "json"
    media_type = "application/json"
    conformance = ("http://www.opengis.net/spec/ogcapi-common-1/1.0/conf/json",)

    _renderer = ORJSONRenderer()

    def render(self, data: Any, context: EncodeContext) -> bytes:
        return self._renderer.render(context.request, data, response_status=context.status)
