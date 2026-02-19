from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Optional


_SENSITIVE_KEY_RE = re.compile(
    r"(?:"
    r"pass(word)?|passwd|secret|token|api[_-]?key|apikey|auth|bearer|signature|sig|"
    r"access[_-]?token|refresh[_-]?token|client[_-]?secret"
    r")",
    re.IGNORECASE,
)


def is_sensitive_key(key: Optional[str]) -> bool:
    if not key:
        return False
    return bool(_SENSITIVE_KEY_RE.search(key))


def redact_value(key: str, value: Any) -> Any:
    if is_sensitive_key(key):
        return "REDACTED"
    if isinstance(value, str) and len(value) > 256:
        return value[:256] + "...(truncated)"
    return value


def redact_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    return {k: redact_value(k, v) for k, v in values.items()}


def summarize_list(values: Iterable[Any], *, max_items: int = 20) -> str:
    items = list(values)
    if len(items) <= max_items:
        return repr(items)
    return (
        repr(items[:max_items])[:-1] + f", ... (+{len(items) - max_items} more)]"
    )
