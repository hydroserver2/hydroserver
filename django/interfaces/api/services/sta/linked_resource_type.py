from core.sta.models import LinkedResourceType
from interfaces.api.services.sta.controlled_vocabulary import ControlledVocabularyAPIService
from interfaces.api.schemas.sta.linked_resource_type import LinkedResourceTypeResponse


class LinkedResourceTypeAPIService(ControlledVocabularyAPIService):
    model = LinkedResourceType
    resource_type_name = "LinkedResourceType"
    response_schema = LinkedResourceTypeResponse
