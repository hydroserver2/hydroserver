from sensorthings import SensorThingsBaseEngine
from sensorthings.extensions.dataarray.engine import DataArrayBaseEngine
from .datastream import DatastreamEngine
from .feature_of_interest import FeatureOfInterestEngine
from .historical_location import HistoricalLocationEngine
from .location import LocationEngine
from .observation import ObservationEngine
from .observed_property import ObservedPropertyEngine
from .sensor import SensorEngine
from .thing import ThingEngine


class HydroServerSensorThingsEngine(
    DatastreamEngine,
    FeatureOfInterestEngine,
    HistoricalLocationEngine,
    LocationEngine,
    ObservationEngine,
    ObservedPropertyEngine,
    SensorEngine,
    ThingEngine,
    SensorThingsBaseEngine,
    DataArrayBaseEngine,
):
    pass
