import uuid
from ninja import Schema, Field, Query
from typing import Optional, Literal
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BasePatchBody,
    CollectionQueryParameters,
)
from interfaces.api.schemas import WorkspaceSummaryResponse


class OrchestrationSystemFields(Schema):
    name: str = Field(..., max_length=255)
    orchestration_system_type: str = Field(..., max_length=255, alias="type")


_order_by_fields = (
    "name",
    "type",
)

OrchestrationSystemOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]


class OrchestrationSystemQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    order_by: Optional[list[OrchestrationSystemOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter orchestration systems by workspace ID."
    )
    orchestration_system_type: list[str] = Query(
        [], description="Filter orchestration systems by type.", alias="type"
    )


class OrchestrationSystemSummaryResponse(BaseGetResponse, OrchestrationSystemFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None


class OrchestrationSystemDetailResponse(BaseGetResponse, OrchestrationSystemFields):
    id: uuid.UUID
    workspace: Optional[WorkspaceSummaryResponse] = None


class OrchestrationSystemPostBody(BasePostBody, OrchestrationSystemFields):
    id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class OrchestrationSystemPatchBody(BasePatchBody, OrchestrationSystemFields):
    pass
