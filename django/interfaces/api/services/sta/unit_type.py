from core.sta.models import UnitType
from interfaces.api.services.sta.controlled_vocabulary import ControlledVocabularyAPIService
from interfaces.api.schemas.sta.unit_type import UnitTypeResponse


class UnitTypeAPIService(ControlledVocabularyAPIService):
    model = UnitType
    resource_type_name = "UnitType"
    response_schema = UnitTypeResponse
