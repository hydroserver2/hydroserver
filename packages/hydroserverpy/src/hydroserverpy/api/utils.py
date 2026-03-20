from uuid import UUID
from typing import Union, Optional, Any
from pydantic.alias_generators import to_camel


def normalize_uuid(
    obj: Optional[Union[str, UUID, Any]],
    attr: str = "uid"
):
    if obj is ...:
        return ...
    if obj is None:
        return None
    if obj and hasattr(obj, attr):
        return str(getattr(obj, attr))
    return str(obj)


def order_by_to_camel(s: str) -> str:
    if s.startswith('-'):
        return '-' + to_camel(s[1:])
    return to_camel(s)
