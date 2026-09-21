from core.sta.models import ResultQualifier
from interfaces.api.services.sta.controlled_vocabulary import ControlledVocabularyAPIService
from interfaces.api.schemas.sta.result_qualifier import ResultQualifierResponse


class ResultQualifierAPIService(ControlledVocabularyAPIService):
    model = ResultQualifier
    resource_type_name = "ResultQualifier"
    response_schema = ResultQualifierResponse
