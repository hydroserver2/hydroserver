from dataclasses import dataclass
from typing import Any, Optional, Union


@dataclass(frozen=True)
class ResponseDocument:
    """
    A response document of a collection's items, or of one item, independent of the format it's encoded in.
    Formats other than JSON encode these rather than the JSON envelope, so they don't depend on its member names.
    """

    items: Union[list[dict], dict]
    number_matched: Optional[int]
    links: list[dict]
    included: Optional[dict[str, list[Any]]]

    @property
    def is_item(self) -> bool:
        return not isinstance(self.items, list)

    @classmethod
    def from_json(cls, data: dict) -> "ResponseDocument":
        """Reads a serialized JSON response document: a PaginatedResponse or an ItemResponse."""

        meta = data.get("meta") or {}

        return cls(
            items=data["data"],
            number_matched=meta.get("numberMatched"),
            links=data.get("links") or [],
            included=data.get("included") or None,
        )
