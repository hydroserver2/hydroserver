from core.sta.models import DatastreamStatus
from interfaces.api.services.sta.controlled_vocabulary import ControlledVocabularyAPIService
from interfaces.api.schemas.sta.datastream_status import DatastreamStatusResponse


class DatastreamStatusAPIService(ControlledVocabularyAPIService):
    model = DatastreamStatus
    resource_type_name = "DatastreamStatus"
    response_schema = DatastreamStatusResponse
