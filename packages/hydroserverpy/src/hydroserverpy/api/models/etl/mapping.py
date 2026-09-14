import uuid
from typing import ClassVar, TYPE_CHECKING
from pydantic import AliasChoices, AliasPath, Field
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class EtlMapping(HydroServerBaseModel):
    task_id: uuid.UUID
    source_identifier: str
    target_datastream_id: uuid.UUID = Field(
        validation_alias=AliasChoices(
            "targetDatastreamId", AliasPath("targetDatastream", "id")
        )
    )

    _editable_fields: ClassVar[set[str]] = {"source_identifier", "target_datastream_id"}

    def __init__(self, client: "HydroServer", task_id: uuid.UUID, **data):
        super().__init__(client=client, service=client.etlmappings, task_id=task_id, **data)

    @classmethod
    def get_route(cls):
        return "etl/mappings"

    def save(self):
        """Save changes to this mapping to HydroServer."""

        if self.unsaved_changes:
            saved = self.client.etlmappings.update(
                task_id=self.task_id, uid=self.uid, **self.unsaved_changes
            )
            self._server_data = saved.dict(by_alias=False).copy()
            self.__dict__.update(saved.__dict__)

    def delete(self):
        """Delete this mapping from HydroServer."""

        self.client.etlmappings.delete(task_id=self.task_id, uid=self.uid)
        self.uid = None
