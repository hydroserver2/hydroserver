import factory

from typing import TYPE_CHECKING
from factory.django import DjangoModelFactory

from processing.products.models import (
    DataProductTask,
    DataProductTransformation,
    DataProductTransformationInput,
    RatingCurve,
    RatingCurvePoint,
)


class DataProductTaskFactory(DjangoModelFactory):
    class Meta:
        model = DataProductTask

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> DataProductTask: ...

    thing = factory.SubFactory("tests.core.sta.factories.ThingFactory")
    name = factory.Sequence(lambda seq: f"Data Product Task {seq}")
    description = factory.Faker("sentence")


class RatingCurveFactory(DjangoModelFactory):
    class Meta:
        model = RatingCurve

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> RatingCurve: ...

    thing = factory.SubFactory("tests.core.sta.factories.ThingFactory")
    name = factory.Sequence(lambda seq: f"Rating Curve {seq}")
    description = factory.Faker("sentence")
    fitting_method = "linear"


class RatingCurvePointFactory(DjangoModelFactory):
    class Meta:
        model = RatingCurvePoint

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> RatingCurvePoint: ...

    rating_curve = factory.SubFactory(RatingCurveFactory)
    input_value = factory.Sequence(lambda seq: float(seq))
    output_value = factory.Sequence(lambda seq: float(seq * 2))


class DataProductTransformationFactory(DjangoModelFactory):
    class Meta:
        model = DataProductTransformation

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> DataProductTransformation: ...

    task = factory.SubFactory(DataProductTaskFactory)
    output_datastream = factory.SubFactory("tests.core.sta.factories.DatastreamFactory")
    transformation_type = "expression"
    formula = "x"


class DataProductTransformationInputFactory(DjangoModelFactory):
    class Meta:
        model = DataProductTransformationInput

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> DataProductTransformationInput: ...

    transformation = factory.SubFactory(DataProductTransformationFactory)
    datastream = factory.SubFactory("tests.core.sta.factories.DatastreamFactory")
    variable_name = None