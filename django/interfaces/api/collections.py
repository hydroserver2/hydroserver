from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CollectionDefinition:
    """
    An OGC API collection, served at /collections/{id} with its items at /collections/{id}/items.

    The router is an import path rather than a Router, so modules the views import (such as the
    response schemas) can use the registry without a circular import.
    """

    id: str
    title: str
    description: str
    router: str
    item_type: Optional[str] = None


VIEWS = "interfaces.api.views"

COLLECTIONS: tuple[CollectionDefinition, ...] = (
    CollectionDefinition(
        id="workspaces",
        title="Workspaces",
        description="Workspaces that own monitoring sites, datastreams, and other data, and "
        "control who can access them.",
        router=f"{VIEWS}.iam.workspace.workspace_router",
    ),
    CollectionDefinition(
        id="roles",
        title="Roles",
        description="Roles that grant collaborators and service accounts permissions within "
        "a workspace.",
        router=f"{VIEWS}.iam.role.role_router",
    ),
    CollectionDefinition(
        id="monitoring-sites",
        title="Monitoring Sites",
        description="Locations where observations are collected, with WGS 84 coordinates.",
        router=f"{VIEWS}.sta.monitoring_site.monitoring_site_router",
        item_type="feature",
    ),
    CollectionDefinition(
        id="monitoring-site-types",
        title="Monitoring Site Types",
        description="Controlled vocabulary of monitoring site types.",
        router=f"{VIEWS}.sta.monitoring_site_type.monitoring_site_type_router",
    ),
    CollectionDefinition(
        id="linked-resource-types",
        title="Linked Resource Types",
        description="Controlled vocabulary of types for files and links attached to monitoring "
        "sites and datastreams.",
        router=f"{VIEWS}.sta.linked_resource_type.linked_resource_type_router",
    ),
    CollectionDefinition(
        id="datastreams",
        title="Datastreams",
        description="Time series of observations of one observed property at a monitoring site.",
        router=f"{VIEWS}.sta.datastream.datastream_router",
        item_type="feature",
    ),
    CollectionDefinition(
        id="datastream-statuses",
        title="Datastream Statuses",
        description="Controlled vocabulary of datastream statuses.",
        router=f"{VIEWS}.sta.datastream_status.datastream_status_router",
    ),
    CollectionDefinition(
        id="aggregation-statistics",
        title="Aggregation Statistics",
        description="Controlled vocabulary of statistics used to aggregate datastream results.",
        router=f"{VIEWS}.sta.aggregation_statistic.aggregation_statistic_router",
    ),
    CollectionDefinition(
        id="observations",
        title="Observations",
        description="Individual timestamped results recorded in datastreams.",
        router=f"{VIEWS}.sta.observation.observation_router",
        item_type="feature",
    ),
    CollectionDefinition(
        id="observed-properties",
        title="Observed Properties",
        description="Phenomena that datastreams observe, such as discharge or water temperature.",
        router=f"{VIEWS}.sta.observed_property.observed_property_router",
    ),
    CollectionDefinition(
        id="observed-property-types",
        title="Observed Property Types",
        description="Controlled vocabulary of observed property types.",
        router=f"{VIEWS}.sta.observed_property_type.observed_property_type_router",
    ),
    CollectionDefinition(
        id="units",
        title="Units",
        description="Units of measure for datastream results.",
        router=f"{VIEWS}.sta.unit.unit_router",
    ),
    CollectionDefinition(
        id="unit-types",
        title="Unit Types",
        description="Controlled vocabulary of unit types.",
        router=f"{VIEWS}.sta.unit_type.unit_type_router",
    ),
    CollectionDefinition(
        id="methods",
        title="Methods",
        description="Sensors and procedures used to produce datastream results.",
        router=f"{VIEWS}.sta.method.method_router",
    ),
    CollectionDefinition(
        id="method-types",
        title="Method Types",
        description="Controlled vocabulary of method types.",
        router=f"{VIEWS}.sta.method_type.method_type_router",
    ),
    CollectionDefinition(
        id="processing-levels",
        title="Processing Levels",
        description="Levels of quality control and processing applied to datastream results.",
        router=f"{VIEWS}.sta.processing_level.processing_level_router",
    ),
    CollectionDefinition(
        id="result-qualifiers",
        title="Result Qualifiers",
        description="Codes that qualify individual observation results.",
        router=f"{VIEWS}.sta.result_qualifier.result_qualifier_router",
    ),
    CollectionDefinition(
        id="sampled-mediums",
        title="Sampled Mediums",
        description="Controlled vocabulary of the media that datastreams sample, such as surface "
        "water or air.",
        router=f"{VIEWS}.sta.sampled_medium.sampled_medium_router",
    ),
    CollectionDefinition(
        id="etl-data-connections",
        title="ETL Data Connections",
        description="Sources that ETL tasks extract data from.",
        router=f"{VIEWS}.etl.data_connection.data_connection_router",
    ),
    CollectionDefinition(
        id="etl-tasks",
        title="ETL Tasks",
        description="Scheduled jobs that load observations from data connections into datastreams.",
        router=f"{VIEWS}.etl.task.etl_task_router",
    ),
    CollectionDefinition(
        id="etl-mappings",
        title="ETL Mappings",
        description="Mappings from source identifiers in extracted data to target datastreams.",
        router=f"{VIEWS}.etl.mapping.etl_mapping_router",
    ),
    CollectionDefinition(
        id="data-product-rating-curves",
        title="Data Product Rating Curves",
        description="Rating curves used by data product transformations.",
        router=f"{VIEWS}.products.rating_curve.rating_curve_router",
    ),
    CollectionDefinition(
        id="data-product-tasks",
        title="Data Product Tasks",
        description="Scheduled jobs that derive datastreams from other datastreams.",
        router=f"{VIEWS}.products.task.data_product_task_router",
    ),
    CollectionDefinition(
        id="data-product-transformations",
        title="Data Product Transformations",
        description="Transformations that data product tasks apply to input datastreams.",
        router=f"{VIEWS}.products.transformation.data_product_transformation_router",
    ),
    CollectionDefinition(
        id="monitoring-tasks",
        title="Monitoring Tasks",
        description="Scheduled jobs that check datastreams against monitoring rules.",
        router=f"{VIEWS}.monitoring.task.monitoring_task_router",
    ),
    CollectionDefinition(
        id="monitoring-rules",
        title="Monitoring Rules",
        description="Conditions that monitoring tasks check datastreams against.",
        router=f"{VIEWS}.monitoring.rule.monitoring_rule_router",
    ),
    CollectionDefinition(
        id="quality-control-histories",
        title="Quality Control Histories",
        description="Records of quality control sessions applied to datastreams.",
        router=f"{VIEWS}.quality.history.qc_history_router",
    ),
)

_COLLECTIONS_BY_ID = {collection.id: collection for collection in COLLECTIONS}


def get_collection(collection_id: str) -> Optional[CollectionDefinition]:
    return _COLLECTIONS_BY_ID.get(collection_id)
