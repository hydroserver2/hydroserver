from typing import Optional
from ninja import NinjaAPI
from ninja.openapi.schema import OpenAPISchema
from ninja.types import DictStrAny

PARAMETER_SERIALIZATION_KEYS = ("style", "explode")


class HydroServerNinjaAPI(NinjaAPI):
    """
    NinjaAPI that moves parameter serialization keywords (style, explode) from a query
    parameter's JSON schema onto its OpenAPI Parameter Object, where OpenAPI reads them.

    Ninja copies a parameter's JSON schema into the Parameter Object's schema as-is, so
    keywords declared there (e.g., by comma_array_schema) would otherwise be ignored and
    clients would fall back to the default explode=true serialization for arrays.
    """

    def get_openapi_schema(
        self,
        *,
        path_prefix: Optional[str] = None,
        path_params: Optional[DictStrAny] = None,
    ) -> OpenAPISchema:
        schema = super().get_openapi_schema(path_prefix=path_prefix, path_params=path_params)

        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                for parameter in operation.get("parameters", []):
                    parameter_schema = parameter.get("schema", {})
                    for key in PARAMETER_SERIALIZATION_KEYS:
                        if key in parameter_schema:
                            parameter[key] = parameter_schema.pop(key)

        return schema
