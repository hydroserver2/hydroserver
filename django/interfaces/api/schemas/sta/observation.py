import uuid

from typing import Optional, Literal, Annotated
from pydantic import AliasPath, AliasChoices, BeforeValidator, WithJsonSchema, model_validator, model_serializer
from pydantic.alias_generators import to_camel
from ninja import Schema, Query, Field

from core.types.iso_datetime import ISODatetime, validate_iso_datetime
from core.sta.models import ResultQualifier
from interfaces.api.schemas import (
    BaseGetResponse,
    BasePostBody,
    BaseQueryParameters,
    CollectionQueryParameters,
    ExtentQueryParameters,
    WorkspaceResponse,
    DatastreamResponse,
    split_comma_separated,
    comma_array_schema,
    split_sortby,
    sortby_array_schema,
)
from interfaces.api.schemas.sta.result_qualifier import ResultQualifierResponse
from interfaces.api.schemas.base import ItemId, NewItemId


class ObservationFields(Schema):
    phenomenon_time: ISODatetime
    result: float
    result_qualifier_codes: list[str] = []


OBSERVATION_INCLUDE_RELATIONS = {
    "datastream": {
        "path": "datastream",
        "bucket": "datastreams",
        "response_schema": DatastreamResponse,
    },
    "workspace": {
        "path": "datastream__monitoring_site__workspace",
        "bucket": "workspaces",
        "response_schema": WorkspaceResponse,
    },
    "resultQualifiers": {
        "bucket": "resultQualifiers",
        "response_schema": ResultQualifierResponse,
        "scoped_vocabulary_model": ResultQualifier,
        "value_field": "result_qualifier_codes",
        "workspace_path": "datastream__monitoring_site__workspace_id",
    },
}
ObservationIncludeRelation = Literal[*OBSERVATION_INCLUDE_RELATIONS.keys()]

_sortby_fields = ("phenomenonTime", "datastreamId")
ObservationSortByFields = Literal[
    *_sortby_fields, *[f"-{f}" for f in _sortby_fields]
]

_property_fields = (
    "id",
    "workspaceId",
    "datastreamId",
    *(to_camel(name) for name in ObservationFields.model_fields),
)
ObservationPropertyName = Literal[*_property_fields]


class ObservationFilterFields(Schema):
    properties: Annotated[
        Optional[list[ObservationPropertyName]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(ObservationPropertyName)),
    ] = Query(
        None,
        description="Comma-separated list of properties to include in the response. "
        "All properties are returned if omitted.",
    )
    include: Annotated[
        Optional[list[ObservationIncludeRelation]],
        BeforeValidator(split_comma_separated),
        WithJsonSchema(comma_array_schema(ObservationIncludeRelation)),
    ] = Query(
        None,
        description="Comma-separated list of related resources to include in the response.",
    )


class ObservationItemQueryParameters(ObservationFilterFields, BaseQueryParameters):
    pass


class ObservationQueryParameters(ObservationFilterFields, CollectionQueryParameters, ExtentQueryParameters):
    datastream_id: list[uuid.UUID] = Query(
        [], description="Filter observations by datastream ID."
    )
    sortby: Annotated[
        Optional[list[ObservationSortByFields]],
        BeforeValidator(split_sortby),
        WithJsonSchema(sortby_array_schema(ObservationSortByFields)),
    ] = Query([], description="Select one or more fields to sort the response by.")
    result_qualifier_codes: list[str] = Query(
        [],
        description="Filter observations by result qualifier code.",
        alias="result_qualifier_code",
    )


class ObservationProperties(BaseGetResponse, ObservationFields):
    workspace_id: uuid.UUID = Field(
        ...,
        validation_alias=AliasChoices(
            "workspaceId", AliasPath("datastream", "monitoring_site", "workspace_id")
        ),
    )
    datastream_id: uuid.UUID


class ObservationResponse(ObservationProperties, ItemId):
    pass


OBSERVATION_GROUP_FIELDS = {
    "id": "id",
    "phenomenonTime": "phenomenon_time",
    "result": "result",
    "resultQualifierCodes": "result_qualifiers",
}
OBSERVATION_GROUP_WORKSPACE_FIELD = "datastream__monitoring_site__workspace_id"

ObservationGroupField = Literal[*OBSERVATION_GROUP_FIELDS]


def without_unselected(data: dict, keys: tuple[str, ...]) -> dict:
    """Leaves out the given members when they're absent (None) because the properties parameter didn't select them."""

    return {key: value for key, value in data.items() if key not in keys or value is not None}


class ObservationGroup(BaseGetResponse):
    """A datastream's observations on a page of the row or column profile."""

    datastream_id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None

    @model_serializer(mode="wrap")
    def _omit_unselected(self, handler):
        return without_unselected(handler(self), ("workspaceId",))

    @staticmethod
    def filter_properties(group: dict, requested: set[str]) -> dict:
        """
        Leaves groups as they are: the observation service reads only the selected properties into them, keeping
        datastreamId, which identifies a group.
        """

        return group


class ObservationRowResponse(ObservationGroup):
    fields: list[ObservationGroupField]
    rows: list[list]


class ObservationColumns(BaseGetResponse):
    id: Optional[list[uuid.UUID]] = None
    phenomenon_time: Optional[list] = None
    result: Optional[list] = None
    result_qualifier_codes: Optional[list] = None

    @model_serializer(mode="wrap")
    def _omit_unselected(self, handler):
        return without_unselected(handler(self), tuple(OBSERVATION_GROUP_FIELDS))


class ObservationColumnResponse(ObservationGroup):
    columns: ObservationColumns


class ObservationPostBody(BasePostBody, ObservationFields, NewItemId):
    datastream_id: uuid.UUID


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
    datastream_id: uuid.UUID
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


class ObservationBulkColumnarPostBody(BasePostBody):
    datastream_id: uuid.UUID
    phenomenon_time: list[ISODatetime]
    result: list[Optional[float]]
    result_qualifier_codes: list[list[str]] = []

    @model_validator(mode="after")
    def validate_lengths(self):
        n = len(self.phenomenon_time)
        if len(self.result) != n:
            raise ValueError("result must have the same length as phenomenonTime")
        if self.result_qualifier_codes and len(self.result_qualifier_codes) != n:
            raise ValueError(
                "resultQualifierCodes must have the same length as phenomenonTime"
            )
        if not self.result_qualifier_codes:
            self.result_qualifier_codes = [[] for _ in range(n)]
        return self

    @property
    def fields(self) -> list[str]:
        return ["phenomenonTime", "result", "resultQualifierCodes"]

    @property
    def data(self) -> list[tuple]:
        return list(zip(self.phenomenon_time, self.result, self.result_qualifier_codes))


class ObservationBulkDeleteBody(BasePostBody):
    datastream_id: uuid.UUID
    phenomenon_time_start: Optional[ISODatetime] = None
    phenomenon_time_end: Optional[ISODatetime] = None
