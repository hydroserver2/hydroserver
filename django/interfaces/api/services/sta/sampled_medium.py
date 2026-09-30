from core.sta.models import SampledMedium
from interfaces.api.services.sta.vocabulary import VocabularyAPIService
from interfaces.api.schemas.sta.sampled_medium import SampledMediumResponse


class SampledMediumAPIService(VocabularyAPIService):
    model = SampledMedium
    resource_type_name = "SampledMedium"
    response_schema = SampledMediumResponse
