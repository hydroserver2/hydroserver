from core.sta.models import AggregationStatistic
from interfaces.api.services.sta.controlled_vocabulary import ControlledVocabularyAPIService
from interfaces.api.schemas.sta.aggregation_statistic import AggregationStatisticResponse


class AggregationStatisticAPIService(ControlledVocabularyAPIService):
    model = AggregationStatistic
    resource_type_name = "AggregationStatistic"
    response_schema = AggregationStatisticResponse
