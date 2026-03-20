from typing import Any, Iterable


def summarize_list(values: Iterable[Any], *, max_items: int = 20) -> str:
    items = list(values)
    if len(items) <= max_items:
        return repr(items)
    return (
        repr(items[:max_items])[:-1] + f", ... (+{len(items) - max_items} more)]"
    )
