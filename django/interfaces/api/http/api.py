from typing import Any, Optional
from ninja import NinjaAPI
from ninja.openapi.schema import OpenAPISchema
from ninja.types import DictStrAny
from pydantic import BaseModel, create_model
from django.http import HttpRequest, HttpResponse
from django.utils.cache import patch_vary_headers

from interfaces.api.collections import CollectionDefinition
from interfaces.api.formats import EncodeContext, collection_formats
from interfaces.api.formats.profiles import collection_profiles, has_profiles
from interfaces.api.http.links import link_header
from interfaces.api.http.content_negotiation import FORMAT_PARAM, PROFILE_PARAM, items_route

PARAMETER_SERIALIZATION_KEYS = ("style", "explode")


class HydroServerNinjaAPI(NinjaAPI):
    """
    NinjaAPI that encodes collection item responses in their negotiated format and adjusts the OpenAPI
    document Ninja generates.

    Ninja copies a parameter's JSON schema into the Parameter Object's schema as-is, so serialization
    keywords (style, explode) declared there (e.g., by comma_array_schema) are moved onto the Parameter
    Object, where OpenAPI reads them; otherwise clients would fall back to the default explode=true
    serialization for arrays. The f parameter, which negotiate_format reads rather than the views, is
    added to collection item GET operations, along with the media types of the formats that document their
    responses (Format.document_schema).
    """

    def create_response(
        self,
        request: HttpRequest,
        data: Any,
        *,
        status: Optional[int] = None,
        temporal_response: Optional[HttpResponse] = None,
    ) -> HttpResponse:
        response_format = getattr(request, "response_format", None)

        if response_format is None:
            return super().create_response(request, data, status=status, temporal_response=temporal_response)

        if temporal_response:
            status = temporal_response.status_code

        if not 200 <= status < 300:
            response = super().create_response(request, data, status=status, temporal_response=temporal_response)
            response["Content-Type"] = self.get_content_type()
        else:
            context = EncodeContext(request=request, collection=request.response_collection, status=status)
            content = response_format.render(data, context)

            if temporal_response:
                response = temporal_response
                response.content = content
            else:
                response = HttpResponse(content, status=status)

            response["Content-Type"] = response_format.content_type

            if not response_format.links_in_body and isinstance(data, dict) and data.get("links"):
                response["Link"] = link_header(data["links"])

        patch_vary_headers(response, ["Accept"])

        return response

    def get_openapi_schema(
        self,
        *,
        path_prefix: Optional[str] = None,
        path_params: Optional[DictStrAny] = None,
    ) -> OpenAPISchema:
        schema = super().get_openapi_schema(path_prefix=path_prefix, path_params=path_params)

        for path, path_item in schema.get("paths", {}).items():
            for operation in path_item.values():
                for parameter in operation.get("parameters", []):
                    parameter_schema = parameter.get("schema", {})
                    for key in PARAMETER_SERIALIZATION_KEYS:
                        if key in parameter_schema:
                            parameter[key] = parameter_schema.pop(key)

            route = items_route(path)
            if route is not None and "get" in path_item:
                collection = route.collection
                path_item["get"].setdefault("parameters", []).append(format_parameter(collection))

                if not route.is_item and has_profiles(collection):
                    path_item["get"]["parameters"].append(profile_parameter(collection))

                kind = "item" if route.is_item else "items"
                responses = path_item["get"]["responses"]
                content = (responses.get(200) or responses["200"])["content"]
                for fmt in collection_formats(collection):
                    model = fmt.document_schema(collection, kind)
                    if model is not None:
                        content[fmt.media_type] = {"schema": self.response_schema(schema, model)}

        return schema

    @staticmethod
    def response_schema(schema: OpenAPISchema, model: type[BaseModel]) -> DictStrAny:
        """
        A reference to a response model's schema, added to the document's components. This deliberately calls
        Ninja's own (private) response model path, which wraps a model in a single "response" field the way
        operations' response models are, so these schemas are generated exactly like Ninja's.
        """

        wrapper = create_model("Response", response=(model, ...))

        return schema._create_schema_from_model(wrapper, mode="serialization")[0]  # noqa


def format_parameter(collection: CollectionDefinition) -> dict:
    """The OpenAPI Parameter Object for the f parameter of a collection's item GET operations."""

    keys = [fmt.key for fmt in collection_formats(collection)]

    return {
        "name": FORMAT_PARAM,
        "in": "query",
        "required": False,
        "description": "Response format. Overrides the Accept header.",
        "schema": {"type": "string", "enum": keys, "default": keys[0]},
    }


def profile_parameter(collection: CollectionDefinition) -> dict:
    """
    The OpenAPI Parameter Object for the profile parameter of a collection's items GET operation.
    """

    by_format = {fmt.key: collection_profiles(collection, fmt.key) for fmt in collection_formats(collection)}
    profiles = list(dict.fromkeys(profile for profiles in by_format.values() for profile in profiles))
    listing = "; ".join(
        f"{profile.uri}: {profile.title} ({', '.join(key for key, supported in by_format.items() if profile in supported)})"
        for profile in profiles
    )

    return {
        "name": PROFILE_PARAM,
        "in": "query",
        "required": False,
        "style": "form",
        "explode": False,
        "description": (
            "Profiles to represent the items in, by URI, in order of preference. Profiles the response format "
            "doesn't support are ignored, and without a supported profile the items are in the format's standard "
            f"representation. Profiles: {listing}."
        ),
        "schema": {"type": "array", "items": {"type": "string", "enum": [profile.uri for profile in profiles]}},
    }
