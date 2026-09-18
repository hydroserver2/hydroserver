from core.sta.models import SampledMedium
from interfaces.api.services.sta.controlled_vocabulary import ControlledVocabularyAPIService
from interfaces.api.schemas.sta.sampled_medium import SampledMediumResponse


class SampledMediumAPIService(ControlledVocabularyAPIService):
    model = SampledMedium
    resource_type_name = "SampledMedium"
    response_schema = SampledMediumResponse
