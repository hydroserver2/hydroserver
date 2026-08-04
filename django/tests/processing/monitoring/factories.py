import factory

from typing import TYPE_CHECKING
from factory.django import DjangoModelFactory

from processing.monitoring.models import MonitoringTask, MonitoringRule


class MonitoringTaskFactory(DjangoModelFactory):
    class Meta:
        model = MonitoringTask

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> MonitoringTask: ...

    thing = factory.SubFactory("tests.core.sta.factories.ThingFactory")
    name = factory.Sequence(lambda seq: f"Monitoring Task {seq}")
    description = factory.Faker("sentence")


class MonitoringRuleFactory(DjangoModelFactory):
    class Meta:
        model = MonitoringRule

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> MonitoringRule: ...

    task = factory.SubFactory(MonitoringTaskFactory)
    datastream = factory.SubFactory("tests.core.sta.factories.DatastreamFactory")
    rule_type = "missing_data"
    window_interval = 1
    window_interval_units = "days"