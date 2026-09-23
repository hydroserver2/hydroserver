from core.sta.models import MethodType
from interfaces.api.services.sta.vocabulary import VocabularyAPIService
from interfaces.api.schemas.sta.method_type import MethodTypeResponse


class MethodTypeAPIService(VocabularyAPIService):
    model = MethodType
    resource_type_name = "MethodType"
    response_schema = MethodTypeResponse
