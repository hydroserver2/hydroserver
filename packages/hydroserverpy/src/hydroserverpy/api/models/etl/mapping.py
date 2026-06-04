import uuid
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class EtlDatastreamSummary(BaseModel):
    id: uuid.UUID
    name: str

    model_config = ConfigDict(populate_by_name=True)


class EtlMapping(BaseModel):
    source_identifier: str
    target_datastream: EtlDatastreamSummary

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
