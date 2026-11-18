from core.sta.models import ZReference
from interfaces.api.services.sta.vocabulary import VocabularyAPIService
from interfaces.api.schemas.sta.z_reference import ZReferenceResponse


class ZReferenceAPIService(VocabularyAPIService):
    model = ZReference
    resource_type_name = "ZReference"
    response_schema = ZReferenceResponse
