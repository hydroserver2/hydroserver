from django.conf import settings
from django.core.cache import cache


PUBLIC_THING_MARKERS_CACHE_KEY = "sta:thing-markers:public:v1"


def get_public_thing_markers_cache_timeout() -> int:
    return max(
        int(getattr(settings, "PUBLIC_THING_MARKERS_CACHE_TIMEOUT", 300)),
        0,
    )


def get_public_thing_markers_cache():
    return cache.get(PUBLIC_THING_MARKERS_CACHE_KEY)


def set_public_thing_markers_cache(markers: list[dict]) -> None:
    cache.set(
        PUBLIC_THING_MARKERS_CACHE_KEY,
        markers,
        timeout=get_public_thing_markers_cache_timeout(),
    )


def invalidate_public_thing_markers_cache(*args, **kwargs) -> None:
    cache.delete(PUBLIC_THING_MARKERS_CACHE_KEY)
