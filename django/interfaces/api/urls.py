from ninja.throttling import AnonRateThrottle, AuthRateThrottle
from django.conf import settings
from django.urls import path, include
from django.views.decorators.csrf import ensure_csrf_cookie

from hydroserver import __version__
from interfaces.api.http import handlers
from interfaces.api.http.api import HydroServerNinjaAPI
from interfaces.api.http.query_params import reject_unknown_query_params
from interfaces.api.http.renderer import ORJSONRenderer

from interfaces.api.collections import COLLECTIONS
from interfaces.api.views import qc_history_router, qc_session_router, qc_operation_router
from interfaces.api.views.ogc import API_DESCRIPTION, API_TITLE, ogc_router


rate_limits = settings.API_RATE_LIMITS or {}
throttle_classes = {"anonymous": AnonRateThrottle, "authenticated": AuthRateThrottle}

api = HydroServerNinjaAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=__version__,
    urls_namespace="ogc",
    docs_decorator=ensure_csrf_cookie,
    renderer=ORJSONRenderer(),
    throttle=[cls(rate_limits[k]) for k, cls in throttle_classes.items() if rate_limits.get(k)],
)

handlers.register(api)
api.add_decorator(reject_unknown_query_params, mode="view")

api.add_router("", ogc_router)

for collection in COLLECTIONS:
    api.add_router(f"collections/{collection.id}", collection.router)

qc_history_router.add_router(
    "/items/{history_id}/sessions", qc_session_router, tags=["Quality Control Sessions"]
)
qc_session_router.add_router(
    "/{session_id}/operations", qc_operation_router, tags=["Quality Control Operations"]
)

urlpatterns = [
    path("ogc/", api.urls),
    path("sensorthings/", include("sensorthings.versions.v1_1.urls")),
]
