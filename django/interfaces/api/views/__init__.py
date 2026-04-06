from interfaces.api.views.iam.workspace import workspace_router
from interfaces.api.views.iam.role import role_router
from interfaces.api.views.iam.collaborator import collaborator_router
from interfaces.api.views.iam.api_key import api_key_router

from interfaces.api.views.sta.thing import thing_router
from interfaces.api.views.sta.observed_property import observed_property_router
from interfaces.api.views.sta.processing_level import processing_level_router
from interfaces.api.views.sta.result_qualifier import result_qualifier_router
from interfaces.api.views.sta.sensor import sensor_router
from interfaces.api.views.sta.unit import unit_router
from interfaces.api.views.sta.datastream import datastream_router
from interfaces.api.views.sta.observation import observation_router

from interfaces.api.views.etl.data_connection import data_connection_router
from interfaces.api.views.etl.task import etl_task_router

from interfaces.api.views.products.rating_curve import rating_curve_router
from interfaces.api.views.products.expression import expression_router
from interfaces.api.views.products.task import data_product_task_router

from interfaces.api.views.monitoring.task import monitoring_task_router
from interfaces.api.views.monitoring.rule import monitoring_rule_router
