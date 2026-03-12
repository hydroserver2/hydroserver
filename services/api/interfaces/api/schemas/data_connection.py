import uuid
from typing import Any, Literal, Optional
from ninja import Schema, Field, Query
from interfaces.api.schemas import BaseGetResponse, BasePostBody, BasePatchBody, CollectionQueryParameters
from interfaces.api.schemas import WorkspaceSummaryResponse


_order_by_fields = (
    "name", "type", "extractorType", "transformerType", "loaderType"
)

DataConnectionOrderByFields = Literal[
    *_order_by_fields, *[f"-{f}" for f in _order_by_fields]
]


class DataConnectionQueryParameters(CollectionQueryParameters):
    order_by: list[DataConnectionOrderByFields] | None = Query(
        [], description="Select one or more fields to order the response by."
    )
    workspace_id: list[uuid.UUID | Literal["null"]] = Query(
        [], description="Filter data connections by workspace ID."
    )
    data_connection_type: list[str] = Query(
        [], description="Filters by the type of the data connection.", alias="type"
    )
    extractor_type: list[str | Literal["null"]] = Query(
        [], description="Filters by the extractor type of the data connection.",
    )
    transformer_type: list[str | Literal["null"]] = Query(
        [], description="Filters by the transformer type of the data connection.",
    )
    loader_type: list[str | Literal["null"]] = Query(
        [], description="Filters by the loader type of the data connection.",
    )
    expand_related: bool | None = None


class DataConnectionSettingsFields(Schema):
    settings_type: str = Field(..., alias="type")
    settings: dict[str, Any]


class DataConnectionSettingsResponse(BaseGetResponse, DataConnectionSettingsFields):
    pass


class DataConnectionSettingsPostBody(BasePostBody, DataConnectionSettingsFields):
    pass


class DataConnectionSettingsPatchBody(BasePatchBody, DataConnectionSettingsFields):
    pass


class DataConnectionFields(Schema):
    name: str
    data_connection_type: str = Field(..., alias="type")


class DataConnectionSummaryResponse(BaseGetResponse, DataConnectionFields):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None
    extractor: DataConnectionSettingsResponse | None = None
    transformer: DataConnectionSettingsResponse | None = None
    loader: DataConnectionSettingsResponse | None = None


class DataConnectionDetailResponse(BaseGetResponse, DataConnectionFields):
    id: uuid.UUID
    workspace: Optional[WorkspaceSummaryResponse] = None
    extractor: DataConnectionSettingsResponse | None = None
    transformer: DataConnectionSettingsResponse | None = None
    loader: DataConnectionSettingsResponse | None = None


class DataConnectionPostBody(BasePostBody, DataConnectionFields):
    id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    extractor: DataConnectionSettingsPostBody | None = None
    transformer: DataConnectionSettingsPostBody | None = None
    loader: DataConnectionSettingsPostBody | None = None


class DataConnectionPatchBody(BasePatchBody, DataConnectionFields):
    extractor: DataConnectionSettingsPatchBody | None = None
    transformer: DataConnectionSettingsPatchBody | None = None
    loader: DataConnectionSettingsPatchBody | None = None
