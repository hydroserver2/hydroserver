from interfaces.api.views.iam.workspace import workspace_router
from interfaces.api.views.iam.role import role_router
from interfaces.api.views.iam.collaborator import collaborator_router
from interfaces.api.views.iam.service_account import service_account_router

from interfaces.api.views.sta.monitoring_site import monitoring_site_router
from interfaces.api.views.sta.monitoring_site_type import monitoring_site_type_router
from interfaces.api.views.sta.linked_resource_type import linked_resource_type_router
from interfaces.api.views.sta.observed_property import observed_property_router
from interfaces.api.views.sta.observed_property_type import observed_property_type_router
from interfaces.api.views.sta.processing_level import processing_level_router
from interfaces.api.views.sta.result_qualifier import result_qualifier_router
from interfaces.api.views.sta.sampled_medium import sampled_medium_router
from interfaces.api.views.sta.aggregation_statistic import aggregation_statistic_router
from interfaces.api.views.sta.datastream_status import datastream_status_router
from interfaces.api.views.sta.method import method_router
from interfaces.api.views.sta.method_type import method_type_router
from interfaces.api.views.sta.unit import unit_router
from interfaces.api.views.sta.unit_type import unit_type_router
from interfaces.api.views.sta.datastream import datastream_router
from interfaces.api.views.sta.observation import observation_router

from interfaces.api.views.etl.data_connection import data_connection_router
from interfaces.api.views.etl.task import etl_task_router
from interfaces.api.views.etl.mapping import etl_mapping_router

from interfaces.api.views.products.rating_curve import rating_curve_router
from interfaces.api.views.products.transformation import data_product_transformation_router
from interfaces.api.views.products.task import data_product_task_router

from interfaces.api.views.monitoring.task import monitoring_task_router
from interfaces.api.views.monitoring.rule import monitoring_rule_router

from interfaces.api.views.quality.history import qc_history_router
from interfaces.api.views.quality.session import qc_session_router
from interfaces.api.views.quality.operation import qc_operation_router
