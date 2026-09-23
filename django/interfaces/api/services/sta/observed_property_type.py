from core.sta.models import ObservedPropertyType
from interfaces.api.services.sta.vocabulary import VocabularyAPIService
from interfaces.api.schemas.sta.observed_property_type import ObservedPropertyTypeResponse


class ObservedPropertyTypeAPIService(VocabularyAPIService):
    model = ObservedPropertyType
    resource_type_name = "ObservedPropertyType"
    response_schema = ObservedPropertyTypeResponse
