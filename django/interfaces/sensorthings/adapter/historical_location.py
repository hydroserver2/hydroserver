from ninja.errors import HttpError
from sensorthings.versions.v1_1.dto import EntityResultSetDTO, CollectionDTO
from .utils import SensorThingsUtils


class HistoricalLocationMixin(SensorThingsUtils):

    def get_historical_locations(self, filters=None, orderby=None, group_by=None,
                                  select=None, top=100, skip=0, count=False, context=None):
        if group_by:
            collections = {pid: CollectionDTO(entity_count=0 if count else None, entity_ids=[]) for pid in group_by[1]}
        else:
            collections = {"__UNGROUPED__": CollectionDTO(entity_count=0 if count else None, entity_ids=[])}
        return EntityResultSetDTO(collections=collections, entities={})

    def create_historical_locations(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def update_historical_locations(self, payload, context=None):
        raise HttpError(403, "This operation is not permitted.")

    def delete_historical_locations(self, entity_ids, context=None):
        raise HttpError(403, "This operation is not permitted.")
