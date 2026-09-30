from core.sta.models import UnitType
from interfaces.api.services.sta.vocabulary import VocabularyAPIService
from interfaces.api.schemas.sta.unit_type import UnitTypeResponse


class UnitTypeAPIService(VocabularyAPIService):
    model = UnitType
    resource_type_name = "UnitType"
    response_schema = UnitTypeResponse
