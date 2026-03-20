import uuid
from pydantic import AliasPath, AliasChoices, model_validator
from ninja import Schema, Query, Field
from typing import Optional, Literal, TYPE_CHECKING
from interfaces.api.types import ISODatetime
from interfaces.api.types.iso_datetime import validate_iso_datetime
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    CollectionQueryParameters,
)

if TYPE_CHECKING:
    from interfaces.api.schemas import WorkspaceSummaryResponse
    from interfaces.api.schemas import DatastreamSummaryResponse


class ObservationFields(Schema):
    phenomenon_time: ISODatetime
    result: float
    result_qualifier_codes: list[str] = []


_order_by_fields = ("phenomenonTime",)

ObservationOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]


class ObservationQueryParameters(CollectionQueryParameters):
    expand_related: Optional[bool] = None
    order_by: Optional[list[ObservationOrderByFields]] = Query(
        [], description="Select one or more fields to order the response by."
    )
    response_format: Optional[Literal["record", "row", "column"]] = Query(
        None,
        description="Controls the format of the observations response.",
        alias="format",
    )
    phenomenon_time__lte: Optional[ISODatetime] = Query(
        None,
        description="Sets the maximum phenomenon time of filtered observations.",
        alias="phenomenon_time_max",
    )
    phenomenon_time__gte: Optional[ISODatetime] = Query(
        None,
        description="Sets the minimum phenomenon time of filtered observations.",
        alias="phenomenon_time_min",
    )
    result_qualifiers__code: list[str] = Query(
        [],
        description="Filter observations by result qualifier code.",
        alias="result_qualifier_code",
    )


class ObservationSummaryResponse(BaseGetResponse, ObservationFields):
    id: uuid.UUID
    workspace_id: uuid.UUID = Field(
        ...,
        validation_alias=AliasChoices(
            "workspaceId", AliasPath("datastream", "thing", "workspace_id")
        ),
    )
    datastream_id: uuid.UUID


class ObservationDetailResponse(BaseGetResponse, ObservationFields):
    id: uuid.UUID
    workspace: "WorkspaceSummaryResponse" = Field(
        ..., validation_alias=AliasPath("datastream", "thing", "workspace")
    )
    datastream: "DatastreamSummaryResponse"


class ObservationRowResponse(BaseGetResponse):
    fields: list[Literal["phenomenonTime", "result", "resultQualifierCodes"]]
    data: list[list]


class ObservationColumnarResponse(BaseGetResponse):
    phenomenon_time: list
    result: list
    result_qualifier_codes: list


class ObservationPostBody(BasePostBody, ObservationFields):
    id: Optional[uuid.UUID] = None


class ObservationBulkPostQueryParameters(Schema):
    mode: Optional[Literal["insert", "append", "backfill", "replace"]] = Query(
        None,
        description=(
            "Specifies how new observations are added to the datastream. "
            "`insert` allows observations at any timestamp. "
            "`append` adds only future observations (after the latest existing timestamp). "
            "`backfill` adds only historical observations (before the earliest existing timestamp). "
            "`replace` deletes all observations in the range of provided observations before inserting new ones."
        ),
    )


class ObservationBulkPostBody(BasePostBody):
    fields: list[Literal["phenomenonTime", "result", "resultQualifierCodes"]]
    data: list[list]

    @model_validator(mode="after")
    def convert_data(self):
        field_map = {field: idx for idx, field in enumerate(self.fields)}
        rows = self.data

        phenomenon_time_idx = field_map.get("phenomenonTime")
        result_idx = field_map.get("result")

        for row in rows:
            if phenomenon_time_idx is not None and isinstance(
                row[phenomenon_time_idx], str
            ):
                row[phenomenon_time_idx] = validate_iso_datetime(
                    row[phenomenon_time_idx]
                )
            if result_idx is not None and row[result_idx] is not None:
                row[result_idx] = float(row[result_idx])

        return self


class ObservationBulkDeleteBody(BasePostBody):
    phenomenon_time_start: Optional[ISODatetime] = None
    phenomenon_time_end: Optional[ISODatetime] = None
