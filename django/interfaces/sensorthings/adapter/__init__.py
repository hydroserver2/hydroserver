from sensorthings.versions.v1_1.backends.base import BaseBackendAdapter
from .thing import ThingMixin
from .location import LocationMixin
from .historical_location import HistoricalLocationMixin
from .sensor import SensorMixin
from .observed_property import ObservedPropertyMixin
from .datastream import DatastreamMixin
from .observation import ObservationMixin
from .feature_of_interest import FeatureOfInterestMixin


class HydroServerAdapter(
    ThingMixin,
    LocationMixin,
    HistoricalLocationMixin,
    SensorMixin,
    ObservedPropertyMixin,
    DatastreamMixin,
    ObservationMixin,
    FeatureOfInterestMixin,
    BaseBackendAdapter,
):
    pass
