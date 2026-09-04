from ninja import NinjaAPI
from ninja.throttling import AnonRateThrottle, AuthRateThrottle
from django.conf import settings
from django.urls import path, include
from django.views.decorators.csrf import ensure_csrf_cookie

from hydroserver import __version__
from interfaces.api.http import handlers
from interfaces.api.http.renderer import ORJSONRenderer

from interfaces.api.views import (
    workspace_router,
    role_router,
    monitoring_site_router,
    observed_property_router,
    processing_level_router,
    result_qualifier_router,
    method_router,
    unit_router,
    datastream_router,
    data_connection_router,
    etl_task_router,
    rating_curve_router,
    rating_curve_transformation_router,
    derivation_transformation_router,
    aggregation_transformation_router,
    data_product_task_router,
    monitoring_task_router,
    monitoring_rule_router,
    qc_history_router,
    qc_session_router,
    qc_operation_router,
)


rate_limits = settings.API_RATE_LIMITS or {}
throttle_classes = {"anonymous": AnonRateThrottle, "authenticated": AuthRateThrottle}

api = NinjaAPI(
    title="HydroServer Data Management API",
    version=__version__,
    urls_namespace="data",
    docs_decorator=ensure_csrf_cookie,
    renderer=ORJSONRenderer(),
    throttle=[cls(rate_limits[k]) for k, cls in throttle_classes.items() if rate_limits.get(k)],
)

handlers.register(api)

api.add_router("workspaces", workspace_router)
api.add_router("roles", role_router)

api.add_router("monitoring-sites", monitoring_site_router)
api.add_router("datastreams", datastream_router)
api.add_router("observed-properties", observed_property_router)
api.add_router("units", unit_router)
api.add_router("methods", method_router)
api.add_router("processing-levels", processing_level_router)
api.add_router("result-qualifiers", result_qualifier_router)

api.add_router("etl/data-connections", data_connection_router)
api.add_router("etl/tasks", etl_task_router)

api.add_router("products/rating-curves", rating_curve_router)
api.add_router("products/tasks", data_product_task_router)
data_product_task_router.add_router("/{task_id}/transformations/rating-curve", rating_curve_transformation_router)
data_product_task_router.add_router("/{task_id}/transformations/derivation", derivation_transformation_router)
data_product_task_router.add_router("/{task_id}/transformations/aggregation", aggregation_transformation_router)

monitoring_task_router.add_router("/{task_id}/rules", monitoring_rule_router)
api.add_router("monitoring/tasks", monitoring_task_router)

api.add_router("quality-control/histories", qc_history_router)
qc_history_router.add_router("/{history_id}/sessions", qc_session_router)
qc_session_router.add_router("/{session_id}/operations", qc_operation_router)

urlpatterns = [
    path("data/", api.urls),
    path("sensorthings/", include("sensorthings.versions.v1_1.urls")),
]
