from uuid import UUID
from datetime import datetime, timezone
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


def sortby_to_camel(s: str) -> str:
    if s.startswith('-'):
        return '-' + to_camel(s[1:])
    return to_camel(s)


def build_datetime_interval(
    start: Optional[Union[datetime, str, Any]],
    end: Optional[Union[datetime, str, Any]],
):
    """
    Builds an OGC API datetime interval ("start/end", with ".." for an open end) from optional
    start and end values. Returns ... when neither is set. Datetimes and ISO 8601 strings without
    a UTC offset are treated as UTC.
    """

    def to_rfc3339(value) -> str:
        if value is ... or value is None:
            return ".."
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    if start in (..., None) and end in (..., None):
        return ...

    return f"{to_rfc3339(start)}/{to_rfc3339(end)}"
