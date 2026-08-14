import uuid
from pydantic import AliasChoices, AliasPath, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class EtlMapping(BaseModel):
    source_identifier: str
    target_datastream_id: uuid.UUID = Field(
        validation_alias=AliasChoices(
            "targetDatastreamId", AliasPath("targetDatastream", "id")
        )
    )

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
