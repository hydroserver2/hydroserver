import factory

from datetime import timedelta
from typing import TYPE_CHECKING
from django.utils import timezone
from factory.django import DjangoModelFactory

from core.sta.models import (
    Datastream,
    Location,
    Observation,
    ObservedProperty,
    ProcessingLevel,
    ResultQualifier,
    Sensor,
    Thing,
    Unit,
)
from tests.core.iam.factories import WorkspaceFactory


class ThingFactory(DjangoModelFactory):
    class Meta:
        model = Thing

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> Thing: ...

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda seq: f"Site {seq}")
    description = factory.Faker("sentence")
    sampling_feature_type = "Site"
    sampling_feature_code = factory.Sequence(lambda seq: f"SITE-{seq}")
    site_type = "Stream"
    is_private = False

    location = factory.RelatedFactory(
        "tests.core.sta.factories.LocationFactory",
        factory_related_name="thing",
        latitude=40.0,
        longitude=-111.0,
    )

    class Params:
        private = factory.Trait(is_private=True)


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> Location: ...

    thing = factory.SubFactory(ThingFactory)
    name = factory.Sequence(lambda seq: f"Location {seq}")
    description = factory.Faker("sentence")
    encoding_type = "application/geo+json"
    latitude = factory.Faker(
        "pydecimal", left_digits=2, right_digits=6, min_value=-90, max_value=90
    )
    longitude = factory.Faker(
        "pydecimal", left_digits=3, right_digits=6, min_value=-180, max_value=180
    )


class SensorFactory(DjangoModelFactory):
    class Meta:
        model = Sensor

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> Sensor: ...

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda seq: f"Sensor {seq}")
    description = factory.Faker("sentence")
    encoding_type = "application/json"
    manufacturer = factory.Faker("company")
    sensor_model = factory.Faker("word")
    method_type = "Instrument deployment"

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

    thing = factory.SubFactory(ThingFactory)
    sensor = factory.SubFactory(
        SensorFactory, workspace=factory.SelfAttribute("..thing.workspace")
    )
    observed_property = factory.SubFactory(
        ObservedPropertyFactory, workspace=factory.SelfAttribute("..thing.workspace")
    )
    processing_level = factory.SubFactory(
        ProcessingLevelFactory, workspace=factory.SelfAttribute("..thing.workspace")
    )
    unit = factory.SubFactory(
        UnitFactory, workspace=factory.SelfAttribute("..thing.workspace")
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
