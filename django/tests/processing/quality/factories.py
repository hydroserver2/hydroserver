import factory

from typing import TYPE_CHECKING
from datetime import timedelta
from django.utils import timezone
from factory.django import DjangoModelFactory

from processing.quality.models import QCHistory, QCOperation, QCSession


class QCHistoryFactory(DjangoModelFactory):
    class Meta:
        model = QCHistory

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> QCHistory: ...

    managed_datastream = factory.SubFactory("tests.core.sta.factories.DatastreamFactory")
    source_datastream = factory.SubFactory("tests.core.sta.factories.DatastreamFactory")


class QCSessionFactory(DjangoModelFactory):
    class Meta:
        model = QCSession

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> QCSession: ...

    history = factory.SubFactory(QCHistoryFactory)
    phenomenon_time_start = factory.LazyFunction(lambda: timezone.now() - timedelta(days=1))
    phenomenon_time_end = factory.LazyFunction(timezone.now)
    source_checksum = "0" * 16

    class Params:
        committed = factory.Trait(
            status="committed",
            committed_at=factory.LazyFunction(timezone.now),
            managed_checksum="0" * 16,
        )


class QCOperationFactory(DjangoModelFactory):
    class Meta:
        model = QCOperation

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> QCOperation: ...

    session = factory.SubFactory(QCSessionFactory)
    order = factory.Sequence(lambda seq: seq)
    operation_type = "SELECTION"
    arguments = factory.LazyFunction(dict)