import uuid
from datetime import datetime
from typing import Optional, Literal, Annotated
from pydantic import BeforeValidator, WithJsonSchema
from pydantic.alias_generators import to_camel
from ninja import Schema, Query

from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    DatastreamResponse,
    split_comma_separated,
    comma_array_schema,
)


WindowIntervalUnits = Literal["minutes", "hours", "days"]
RuleType = Literal["range", "rate_of_change", "persistence", "missing_data"]


class MonitoringRuleFields(Schema):
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    window_interval: Optional[int] = None
    window_interval_units: Optional[WindowIntervalUnits] = None


MONITORING_RULE_INCLUDE_RELATIONS = {
    "datastream": {
        "path": "datastream",
        "bucket": "datastreams",
        "response_schema": DatastreamResponse,
    },
}
MonitoringRuleIncludeRelation = Literal[*MONITORING_RULE_INCLUDE_RELATIONS.keys()]

_order_by_fields = ("id", "ruleType", "datastreamId")
MonitoringRuleOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]

_property_fields = (
    "id",
    "datastreamId",
    "ruleType",
    "lastCheckedAt",
    *(to_camel(name) for name in MonitoringRuleFields.model_fields),
)
MonitoringRulePropertyName = Literal[*_property_fields]


class MonitoringRuleFilterFields(Schema):
    properties: Annotated[
        Optional[list[MonitoringRulePropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(MonitoringRulePropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[MonitoringRuleIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(MonitoringRuleIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class MonitoringRuleItemQueryParameters(MonitoringRuleFilterFields, BaseQueryParameters):
    pass


class MonitoringRuleQueryParameters(MonitoringRuleFilterFields, CollectionQueryParameters):
    order_by: Optional[list[MonitoringRuleOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    datastream_id: list[uuid.UUID] = Query(
        [], description="Filter rules by datastream ID."
    )
    rule_type: list[str] = Query(
        [], description="Filter rules by rule type."
    )


class MonitoringRuleResponse(BaseGetResponse, MonitoringRuleFields):
    id: uuid.UUID
    datastream_id: uuid.UUID
    rule_type: RuleType
    last_checked_at: Optional[datetime] = None


class MonitoringRulePostBody(BasePostBody, MonitoringRuleFields):
    id: Optional[uuid.UUID] = None
    datastream_id: uuid.UUID
    rule_type: RuleType


class MonitoringRulePatchBody(BasePatchBody, MonitoringRuleFields):
    pass
