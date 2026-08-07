from django.conf import settings
from django.core.cache import cache


PUBLIC_MONITORING_SITE_MARKERS_CACHE_KEY = "sta:monitoring_site-markers:public:v1"


def get_public_monitoring_site_markers_cache_timeout() -> int:
    return max(
        int(getattr(settings, "PUBLIC_MONITORING_SITE_MARKERS_CACHE_TIMEOUT", 300)),
        0,
    )


def get_public_monitoring_site_markers_cache():
    return cache.get(PUBLIC_MONITORING_SITE_MARKERS_CACHE_KEY)


def set_public_monitoring_site_markers_cache(markers: list[dict]) -> None:
    cache.set(
        PUBLIC_MONITORING_SITE_MARKERS_CACHE_KEY,
        markers,
        timeout=get_public_monitoring_site_markers_cache_timeout(),
    )


def invalidate_public_monitoring_site_markers_cache(*args, **kwargs) -> None:
    cache.delete(PUBLIC_MONITORING_SITE_MARKERS_CACHE_KEY)
