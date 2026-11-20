from core.sta.models import MonitoringSiteType
from interfaces.api.services.sta.vocabulary import VocabularyAPIService
from interfaces.api.schemas.sta.monitoring_site_type import MonitoringSiteTypeResponse


class MonitoringSiteTypeAPIService(VocabularyAPIService):
    model = MonitoringSiteType
    resource_type_name = "MonitoringSiteType"
    response_schema = MonitoringSiteTypeResponse
