import re

from typing import Annotated
from pydantic import AfterValidator

_DURATION_RE = re.compile(r"^(\d+)([mhdw])$")

_UNIT_US: dict[str, int] = {
    "m": 60_000_000,
    "h": 3_600_000_000,
    "d": 86_400_000_000,
    "w": 604_800_000_000,
}


def _validate_duration(v: str) -> str:
    if not _DURATION_RE.match(v):
        raise ValueError(
            f"Invalid duration string '{v}'. "
            "Expected a duration string such as '1h', '30m', or '1d'."
        )
    return v


def duration_to_us(duration: str) -> int:
    """Convert a duration string to microseconds."""

    m = _DURATION_RE.match(duration)

    return int(m.group(1)) * _UNIT_US[m.group(2)]


Duration = Annotated[str, AfterValidator(_validate_duration)]
