import uuid
from datetime import datetime
from typing import Optional, Literal

from ninja import Field, Query

from core.types import Unset
from interfaces.api.schemas import (
    OrderByField,
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
    DatastreamSummaryResponse,
)


WindowIntervalUnits = Literal["minutes", "hours", "days"]
RuleType = Literal["range", "rate_of_change", "persistence", "missing_data"]


class MonitoringRuleOrderBy(OrderByField):
    id = ("id", "id")
    rule_type = ("ruleType", "rule_type")
    datastream_id = ("datastreamId", "datastream_id")


class MonitoringRuleQueryParameters(CollectionQueryParameters):
    order_by: list[MonitoringRuleOrderBy] = Query(
        [], description="Select one or more fields to order the response by."
    )
    datastream: list[uuid.UUID] = Query(
        [], description="Filter rules by datastream ID.", alias="datastream_id"
    )
    rule_type: list[str] = Query(
        [], description="Filter rules by rule type."
    )


class MonitoringRuleResponse(BaseGetResponse):
    id: uuid.UUID
    datastream: DatastreamSummaryResponse
    rule_type: RuleType
    last_checked_at: Optional[datetime] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    window_interval: Optional[int] = None
    window_interval_units: Optional[WindowIntervalUnits] = None

    @staticmethod
    def resolve_datastream(obj):
        return obj.datastream


class MonitoringRuleDetailResponse(BaseGetResponse):
    id: uuid.UUID
    rule_type: RuleType
    last_checked_at: Optional[datetime] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    window_interval: Optional[int] = None
    window_interval_units: Optional[WindowIntervalUnits] = None


class MonitoredDatastreamSummaryResponse(BaseGetResponse):
    datastream_id: uuid.UUID
    rules: list[MonitoringRuleDetailResponse]


class MonitoredDatastreamResponse(BaseGetResponse):
    datastream: DatastreamSummaryResponse
    rules: list[MonitoringRuleDetailResponse]


class MonitoringRulePostBody(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    datastream_id: uuid.UUID
    rule_type: RuleType
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    window_interval: Optional[int] = None
    window_interval_units: Optional[WindowIntervalUnits] = None


class MonitoringRulePatchBody(BasePatchBody):
    min_value: Optional[float]
    max_value: Optional[float]
    window_interval: Optional[int]
    window_interval_units: Optional[WindowIntervalUnits]
