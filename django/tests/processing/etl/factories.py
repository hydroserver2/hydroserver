import factory

from typing import TYPE_CHECKING
from factory.django import DjangoModelFactory

from processing.etl.models import DataConnection, EtlMapping, EtlTask, Payload, PlaceholderVariable
from tests.core.iam.factories import WorkspaceFactory


class DataConnectionFactory(DjangoModelFactory):
    class Meta:
        model = DataConnection

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> DataConnection: ...

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda seq: f"Data Connection {seq}")
    description = factory.Faker("sentence")
    source_url = factory.Faker("url")


class PayloadFactory(DjangoModelFactory):
    class Meta:
        model = Payload

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> Payload: ...

    data_connection = factory.SubFactory(DataConnectionFactory)
    payload_type = "CSV"
    timestamp_key = "timestamp"
    header_row = 1
    data_start_row = 2
    delimiter = ","

    class Params:
        json = factory.Trait(
            payload_type="JSON",
            header_row=None,
            data_start_row=None,
            delimiter=None,
            jmespath="observations",
        )


class PlaceholderVariableFactory(DjangoModelFactory):
    class Meta:
        model = PlaceholderVariable

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> PlaceholderVariable: ...

    data_connection = factory.SubFactory(DataConnectionFactory)
    name = factory.Sequence(lambda seq: f"var_{seq}")
    variable_type = "per_task"


class EtlTaskFactory(DjangoModelFactory):
    class Meta:
        model = EtlTask

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> EtlTask: ...

    data_connection = factory.SubFactory(DataConnectionFactory)
    name = factory.Sequence(lambda seq: f"ETL Task {seq}")
    description = factory.Faker("sentence")
    task_variables = factory.LazyFunction(dict)


class EtlMappingFactory(DjangoModelFactory):
    class Meta:
        model = EtlMapping

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> EtlMapping: ...

    etl_task = factory.SubFactory(EtlTaskFactory)
    source_identifier = factory.Sequence(lambda seq: f"col_{seq}")
    target_datastream = factory.SubFactory("tests.core.sta.factories.DatastreamFactory")