import pytest

from pydantic import ValidationError

from interfaces.api.schemas.sta.aggregation_statistic import (
    AggregationStatisticPostBody,
    AggregationStatisticPatchBody,
)
from interfaces.api.schemas.sta.datastream_status import (
    DatastreamStatusPostBody,
    DatastreamStatusPatchBody,
)
from interfaces.api.schemas.sta.linked_resource_type import (
    LinkedResourceTypePostBody,
    LinkedResourceTypePatchBody,
)
from interfaces.api.schemas.sta.method_type import (
    MethodTypePostBody,
    MethodTypePatchBody,
)
from interfaces.api.schemas.sta.monitoring_site_type import (
    MonitoringSiteTypePostBody,
    MonitoringSiteTypePatchBody,
)
from interfaces.api.schemas.sta.observed_property_type import (
    ObservedPropertyTypePostBody,
    ObservedPropertyTypePatchBody,
)
from interfaces.api.schemas.sta.result_qualifier import (
    ResultQualifierPostBody,
    ResultQualifierPatchBody,
)
from interfaces.api.schemas.sta.sampled_medium import (
    SampledMediumPostBody,
    SampledMediumPatchBody,
)
from interfaces.api.schemas.sta.unit_type import (
    UnitTypePostBody,
    UnitTypePatchBody,
)

BODY_SCHEMAS = [
    AggregationStatisticPostBody,
    AggregationStatisticPatchBody,
    DatastreamStatusPostBody,
    DatastreamStatusPatchBody,
    LinkedResourceTypePostBody,
    LinkedResourceTypePatchBody,
    MethodTypePostBody,
    MethodTypePatchBody,
    MonitoringSiteTypePostBody,
    MonitoringSiteTypePatchBody,
    ObservedPropertyTypePostBody,
    ObservedPropertyTypePatchBody,
    ResultQualifierPostBody,
    ResultQualifierPatchBody,
    SampledMediumPostBody,
    SampledMediumPatchBody,
    UnitTypePostBody,
    UnitTypePatchBody,
]


@pytest.mark.parametrize("schema", BODY_SCHEMAS, ids=lambda s: s.__name__)
@pytest.mark.parametrize("description", ["", None])
def test_body_accepts_blank_description_as_none(schema, description):
    body = schema.model_validate({"name": "Name", "description": description})

    assert body.description is None


@pytest.mark.parametrize("schema", BODY_SCHEMAS, ids=lambda s: s.__name__)
def test_body_rejects_empty_name(schema):
    with pytest.raises(ValidationError):
        schema.model_validate({"name": "", "description": ""})
