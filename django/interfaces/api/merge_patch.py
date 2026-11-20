"""JSON Merge Patch (RFC 7396), shared by model-backed JSON properties."""

from copy import deepcopy
from typing import Any


MERGE_PATCH_MEDIA_TYPE = "application/merge-patch+json"


def merge_patch(target: Any, patch: Any) -> Any:
    """Apply a patch without modifying either input. Arrays replace in full."""
    if not isinstance(patch, dict):
        return deepcopy(patch)

    result = deepcopy(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = merge_patch(result.get(key), value)
    return result
