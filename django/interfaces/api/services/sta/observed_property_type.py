from core.sta.models import ObservedPropertyType
from interfaces.api.services.sta.controlled_vocabulary import ControlledVocabularyAPIService
from interfaces.api.schemas.sta.observed_property_type import ObservedPropertyTypeResponse


class ObservedPropertyTypeAPIService(ControlledVocabularyAPIService):
    model = ObservedPropertyType
    resource_type_name = "ObservedPropertyType"
    response_schema = ObservedPropertyTypeResponse
