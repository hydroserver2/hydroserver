from core.sta.models import DatastreamStatus
from interfaces.api.services.sta.vocabulary import VocabularyAPIService
from interfaces.api.schemas.sta.datastream_status import DatastreamStatusResponse


class DatastreamStatusAPIService(VocabularyAPIService):
    model = DatastreamStatus
    resource_type_name = "DatastreamStatus"
    response_schema = DatastreamStatusResponse
