import uuid
from typing import ClassVar, TYPE_CHECKING
from pydantic import AliasChoices, AliasPath, Field
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class EtlMapping(HydroServerBaseModel):
    task_id: uuid.UUID = Field(validation_alias="etlTaskId")
    source_identifier: str
    target_datastream_id: uuid.UUID = Field(
        validation_alias=AliasChoices(
            "targetDatastreamId", AliasPath("targetDatastream", "id")
        )
    )

    _editable_fields: ClassVar[set[str]] = {"source_identifier", "target_datastream_id"}

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.etlmappings, **data)

    @classmethod
    def get_route(cls):
        return "etl-mappings"
