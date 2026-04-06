import uuid
from datetime import datetime
from typing import Optional, Literal, Union

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


WindowUnits = Literal["minutes", "hours", "days"]


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


# --- Per-type response schemas ---

class RangeRuleResponse(BaseGetResponse):
    rule_type: Literal["range"] = Field(alias="type")
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class RateOfChangeRuleResponse(BaseGetResponse):
    rule_type: Literal["rate_of_change"] = Field(alias="type")
    max_change: float
    window: int
    window_units: WindowUnits


class PersistenceRuleResponse(BaseGetResponse):
    rule_type: Literal["persistence"] = Field(alias="type")
    persist_value: Optional[float] = None
    window: int
    window_units: WindowUnits


class MissingDataRuleResponse(BaseGetResponse):
    rule_type: Literal["missing_data"] = Field(alias="type")
    window: int
    window_units: WindowUnits


# --- Per-type post body schemas ---

class RangeRulePostBody(BasePostBody, RangeRuleResponse):
    ...


class RateOfChangeRulePostBody(BasePostBody, RateOfChangeRuleResponse):
    ...


class PersistenceRulePostBody(BasePostBody, PersistenceRuleResponse):
    ...


class MissingDataRulePostBody(BasePostBody, MissingDataRuleResponse):
    ...


# --- Per-type patch body schemas ---

class RangeRulePatchBody(BasePatchBody, RangeRuleResponse):
    ...


class RateOfChangeRulePatchBody(BasePatchBody, RateOfChangeRuleResponse):
    ...


class PersistenceRulePatchBody(BasePatchBody, PersistenceRuleResponse):
    ...


class MissingDataRulePatchBody(BasePatchBody, MissingDataRuleResponse):
    ...


# --- Shared resolve_rule helper ---

def _resolve_rule(obj) -> dict:
    return {
        "rule_type": obj.rule_type,
        "min_value": obj.min_value,
        "max_value": obj.max_value,
        "max_change": obj.max_change,
        "persist_value": obj.persist_value,
        "window": obj.window,
        "window_units": obj.window_units,
    }


# --- Top-level rule schemas ---

class MonitoringRuleDetailResponse(BaseGetResponse):
    """Rule details without the datastream — used when nested under a MonitoredDatastreamResponse."""
    id: uuid.UUID
    last_checked_at: Optional[datetime] = None
    rule: Union[RangeRuleResponse, RateOfChangeRuleResponse, PersistenceRuleResponse, MissingDataRuleResponse]

    @staticmethod
    def resolve_rule(obj):
        return _resolve_rule(obj)


class MonitoredDatastreamResponse(BaseGetResponse):
    """A datastream and all its rules for a given monitoring task."""
    datastream: DatastreamSummaryResponse
    rules: list[MonitoringRuleDetailResponse]


class MonitoringRuleResponse(BaseGetResponse):
    id: uuid.UUID
    datastream: DatastreamSummaryResponse
    last_checked_at: Optional[datetime] = None
    rule: Union[RangeRuleResponse, RateOfChangeRuleResponse, PersistenceRuleResponse, MissingDataRuleResponse]

    @staticmethod
    def resolve_datastream(obj):
        return obj.datastream

    @staticmethod
    def resolve_rule(obj):
        return _resolve_rule(obj)


class MonitoringRulePostBody(BasePostBody):
    uid: uuid.UUID | Unset = Field(Unset, alias="id")
    datastream_id: uuid.UUID
    rule: Union[RangeRulePostBody, RateOfChangeRulePostBody, PersistenceRulePostBody, MissingDataRulePostBody]


class MonitoringRulePatchBody(BasePatchBody):
    rule: Union[RangeRulePatchBody, RateOfChangeRulePatchBody, PersistenceRulePatchBody, MissingDataRulePatchBody]