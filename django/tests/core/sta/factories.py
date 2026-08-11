import factory

from datetime import timedelta
from typing import TYPE_CHECKING
from django.utils import timezone
from factory.django import DjangoModelFactory

from core.sta.models import (
    Datastream,
    Observation,
    ObservedProperty,
    ProcessingLevel,
    ResultQualifier,
    Method,
    MonitoringSite,
    Unit,
)
from tests.core.iam.factories import WorkspaceFactory


class MonitoringSiteFactory(DjangoModelFactory):
    class Meta:
        model = MonitoringSite

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> MonitoringSite: ...

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda seq: f"Site {seq}")
    description = factory.Faker("sentence")
    code = factory.Sequence(lambda seq: f"SITE-{seq}")
    type = "Stream"
    latitude = 40.0
    longitude = -111.0
    is_private = False

    class Params:
        private = factory.Trait(is_private=True)


class MethodFactory(DjangoModelFactory):
    class Meta:
        model = Method

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> Method: ...

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda seq: f"Method {seq}")
    code = factory.Sequence(lambda seq: f"METHOD-{seq}")
    type = "Instrument Deployment"
    description = factory.Faker("sentence")
    sensor_model = factory.Faker("word")
    sensor_model_manufacturer = factory.Faker("company")
    sensor_model_definition = factory.Faker("url")

    class Params:
        global_ = factory.Trait(workspace=None)


class ObservedPropertyFactory(DjangoModelFactory):
    class Meta:
        model = ObservedProperty

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> ObservedProperty: ...

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda seq: f"Observed Property {seq}")
    definition = factory.Faker("url")
    description = factory.Faker("sentence")
    observed_property_type = "Hydrology"
    code = factory.Sequence(lambda seq: f"OP-{seq}")

    class Params:
        global_ = factory.Trait(workspace=None)


class ProcessingLevelFactory(DjangoModelFactory):
    class Meta:
        model = ProcessingLevel

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> ProcessingLevel: ...

    workspace = factory.SubFactory(WorkspaceFactory)
    code = factory.Sequence(lambda seq: f"Level {seq}")
    definition = factory.Faker("sentence")
    explanation = factory.Faker("paragraph")

    class Params:
        global_ = factory.Trait(workspace=None)


class ResultQualifierFactory(DjangoModelFactory):
    class Meta:
        model = ResultQualifier

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> ResultQualifier: ...

    workspace = factory.SubFactory(WorkspaceFactory)
    code = factory.Sequence(lambda seq: f"RQ-{seq}")
    description = factory.Faker("sentence")

    class Params:
        global_ = factory.Trait(workspace=None)


class UnitFactory(DjangoModelFactory):
    class Meta:
        model = Unit

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> Unit: ...

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda seq: f"Unit {seq}")
    symbol = factory.Sequence(lambda seq: f"u{seq}")
    definition = factory.Faker("sentence")
    unit_type = "Dimensionless"

    class Params:
        global_ = factory.Trait(workspace=None)


class DatastreamFactory(DjangoModelFactory):
    class Meta:
        model = Datastream

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> Datastream: ...

    monitoring_site = factory.SubFactory(MonitoringSiteFactory)
    method = factory.SubFactory(
        MethodFactory, workspace=factory.SelfAttribute("..monitoring_site.workspace")
    )
    observed_property = factory.SubFactory(
        ObservedPropertyFactory, workspace=factory.SelfAttribute("..monitoring_site.workspace")
    )
    processing_level = factory.SubFactory(
        ProcessingLevelFactory, workspace=factory.SelfAttribute("..monitoring_site.workspace")
    )
    unit = factory.SubFactory(
        UnitFactory, workspace=factory.SelfAttribute("..monitoring_site.workspace")
    )
    name = factory.Sequence(lambda seq: f"Datastream {seq}")
    description = factory.Faker("sentence")
    observation_type = "OM_Measurement"
    result_type = "Time Series Coverage"
    sampled_medium = "Water"
    no_data_value = -9999.0
    aggregation_statistic = "Average"
    time_aggregation_interval = 15
    time_aggregation_interval_unit = "minutes"
    is_private = False
    is_visible = True

    class Params:
        private = factory.Trait(is_private=True)


class ObservationFactory(DjangoModelFactory):
    class Meta:
        model = Observation

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> Observation: ...

    datastream = factory.SubFactory(DatastreamFactory)
    phenomenon_time = factory.Sequence(
        lambda seq: timezone.now() - timedelta(minutes=seq)
    )
    result = factory.Faker("pyfloat", left_digits=3, right_digits=3, positive=True)
