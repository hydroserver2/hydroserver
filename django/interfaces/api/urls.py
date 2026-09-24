from ninja.throttling import AnonRateThrottle, AuthRateThrottle
from django.conf import settings
from django.urls import path, include
from django.views.decorators.csrf import ensure_csrf_cookie

from hydroserver import __version__
from interfaces.api.http import handlers
from interfaces.api.http.api import HydroServerNinjaAPI
from interfaces.api.http.renderer import ORJSONRenderer

from interfaces.api.views import (
    workspace_router,
    role_router,
    monitoring_site_router,
    monitoring_site_type_router,
    linked_resource_type_router,
    observed_property_router,
    observed_property_type_router,
    processing_level_router,
    result_qualifier_router,
    sampled_medium_router,
    aggregation_statistic_router,
    datastream_status_router,
    method_router,
    method_type_router,
    unit_router,
    unit_type_router,
    datastream_router,
    observation_router,
    data_connection_router,
    etl_task_router,
    etl_mapping_router,
    rating_curve_router,
    data_product_transformation_router,
    data_product_task_router,
    monitoring_task_router,
    monitoring_rule_router,
    qc_history_router,
    qc_session_router,
    qc_operation_router,
)


rate_limits = settings.API_RATE_LIMITS or {}
throttle_classes = {"anonymous": AnonRateThrottle, "authenticated": AuthRateThrottle}

api = HydroServerNinjaAPI(
    title="HydroServer Data Management API",
    version=__version__,
    urls_namespace="ogc",
    docs_decorator=ensure_csrf_cookie,
    renderer=ORJSONRenderer(),
    throttle=[cls(rate_limits[k]) for k, cls in throttle_classes.items() if rate_limits.get(k)],
)

handlers.register(api)

api.add_router("collections/workspaces", workspace_router)
api.add_router("collections/roles", role_router)

api.add_router("collections/monitoring-sites", monitoring_site_router)
api.add_router("collections/monitoring-site-types", monitoring_site_type_router)
api.add_router("collections/linked-resource-types", linked_resource_type_router)
api.add_router("collections/datastreams", datastream_router)
api.add_router("collections/datastream-statuses", datastream_status_router)
api.add_router("collections/aggregation-statistics", aggregation_statistic_router)
api.add_router("collections/observations", observation_router)
api.add_router("collections/observed-properties", observed_property_router)
api.add_router("collections/observed-property-types", observed_property_type_router)
api.add_router("collections/units", unit_router)
api.add_router("collections/unit-types", unit_type_router)
api.add_router("collections/methods", method_router)
api.add_router("collections/method-types", method_type_router)
api.add_router("collections/processing-levels", processing_level_router)
api.add_router("collections/result-qualifiers", result_qualifier_router)
api.add_router("collections/sampled-mediums", sampled_medium_router)

api.add_router("collections/etl-data-connections", data_connection_router)
api.add_router("collections/etl-tasks", etl_task_router)
api.add_router("collections/etl-mappings", etl_mapping_router)

api.add_router("collections/data-product-rating-curves", rating_curve_router)
api.add_router("collections/data-product-tasks", data_product_task_router)
api.add_router("collections/data-product-transformations", data_product_transformation_router)

api.add_router("collections/monitoring-tasks", monitoring_task_router)
api.add_router("collections/monitoring-rules", monitoring_rule_router)

api.add_router("collections/quality-control-histories", qc_history_router)
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
