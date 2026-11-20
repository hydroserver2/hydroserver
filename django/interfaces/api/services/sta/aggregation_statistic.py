from core.sta.models import AggregationStatistic
from interfaces.api.services.sta.vocabulary import VocabularyAPIService
from interfaces.api.schemas.sta.aggregation_statistic import AggregationStatisticResponse


class AggregationStatisticAPIService(VocabularyAPIService):
    model = AggregationStatistic
    resource_type_name = "AggregationStatistic"
    response_schema = AggregationStatisticResponse
