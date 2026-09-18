from core.sta.models import MethodType
from interfaces.api.services.sta.controlled_vocabulary import ControlledVocabularyAPIService
from interfaces.api.schemas.sta.method_type import MethodTypeResponse


class MethodTypeAPIService(ControlledVocabularyAPIService):
    model = MethodType
    resource_type_name = "MethodType"
    response_schema = MethodTypeResponse
