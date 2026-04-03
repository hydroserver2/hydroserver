from typing import Any, Union
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


class UnsetType:
    """
    Singleton type representing a field or value that is intentionally absent.

    This can be used in Pydantic models to mark a value as unset or excluded
    from serialization.
    """

    def __repr__(self) -> str:
        """Return a string representation of the UnsetType singleton."""

        return "<UNSET>"

    def __bool__(self) -> bool:
        """Always evaluate as False in boolean contexts."""

        return False

    def __or__(self, other):
        return Union[self.__class__, other]

    def __ror__(self, other):
        return Union[other, self.__class__]

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """
        Return a Pydantic core schema for UnsetType.

        This allows Pydantic models to validate and serialize fields
        using this type.
        """

        def serialize(value: Any) -> None:
            """Serialize UnsetType as None for JSON output."""

            return None

        def validate(value: Any) -> "UnsetType":
            """Validate any value as UnsetType."""

            return value

        schema = core_schema.union_schema(
            [
                core_schema.is_instance_schema(cls),
            ]
        )

        return core_schema.no_info_after_validator_function(
            validate,
            schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                serialize, when_used="json"
            ),
        )


Unset = UnsetType()
