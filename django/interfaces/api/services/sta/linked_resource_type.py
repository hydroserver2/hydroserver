from core.sta.models import LinkedResourceType
from interfaces.api.services.sta.vocabulary import VocabularyAPIService
from interfaces.api.schemas.sta.linked_resource_type import LinkedResourceTypeResponse


class LinkedResourceTypeAPIService(VocabularyAPIService):
    model = LinkedResourceType
    resource_type_name = "LinkedResourceType"
    response_schema = LinkedResourceTypeResponse
