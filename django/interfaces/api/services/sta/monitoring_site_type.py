from core.sta.models import MonitoringSiteType
from interfaces.api.services.sta.controlled_vocabulary import ControlledVocabularyAPIService
from interfaces.api.schemas.sta.monitoring_site_type import MonitoringSiteTypeResponse


class MonitoringSiteTypeAPIService(ControlledVocabularyAPIService):
    model = MonitoringSiteType
    resource_type_name = "MonitoringSiteType"
    response_schema = MonitoringSiteTypeResponse
