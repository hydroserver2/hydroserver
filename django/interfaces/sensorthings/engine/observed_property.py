from uuid import UUID
from typing import Optional
from ninja.errors import HttpError
from django.db.utils import DataError, DatabaseError
from domains.sta.models import ObservedProperty
from sensorthings.components.observedproperties.engine import ObservedPropertyBaseEngine
from sensorthings.components.observedproperties.schemas import (
    ObservedProperty as ObservedPropertySchema,
)
from .utils import SensorThingsUtils


class ObservedPropertyEngine(ObservedPropertyBaseEngine, SensorThingsUtils):
    def get_observed_properties(
        self,
        observed_property_ids: Optional[list[UUID]] = None,
        pagination: Optional[dict] = None,
        ordering: Optional[dict] = None,
        filters: Optional[dict] = None,
        expanded: bool = False,
        get_count: bool = False,
    ) -> (list[dict], int):

        if observed_property_ids:
            observed_property_ids = self.strings_to_uuids(observed_property_ids)

        observed_properties = ObservedProperty.objects

        if observed_property_ids:
            observed_properties = observed_properties.filter(
                id__in=observed_property_ids
            )

        observed_properties = observed_properties.visible(
            principal=self.request.principal  # noqa
        )

        if filters:
            observed_properties = self.apply_filters(
                queryset=observed_properties,
                component=ObservedPropertySchema,
                filters=filters,
            )

        if ordering:
            observed_properties = self.apply_order(
                queryset=observed_properties,
                component=ObservedPropertySchema,
                order_by=ordering,
            )

        observed_properties = observed_properties.distinct()

        if get_count:
            count = observed_properties.count()
        else:
            count = None

        if pagination:
            observed_properties = self.apply_pagination(
                queryset=observed_properties,
                top=pagination.get("top"),
                skip=pagination.get("skip"),
            )

        try:
            return {
                observed_property.id: {
                    "id": observed_property.id,
                    "name": observed_property.name,
                    "description": observed_property.description,
                    "definition": observed_property.definition,
                    "properties": {
                        "variable_code": observed_property.code,
                        "variable_type": observed_property.observed_property_type,
                        "workspace": (
                            {
                                "id": observed_property.workspace.id,
                                "name": observed_property.workspace.name,
                                "link": observed_property.workspace.link,
                                "is_private": observed_property.workspace.is_private,
                            }
                            if observed_property.workspace
                            else None
                        ),
                    },
                }
                for observed_property in observed_properties
            }, count
        except (
            DataError,
            DatabaseError,
        ) as e:
            raise HttpError(400, str(e))

    def create_observed_property(self, observed_property) -> str:
        raise HttpError(403, "You do not have permission to perform this action.")

    def update_observed_property(
        self, observed_property_id: str, observed_property
    ) -> None:
        raise HttpError(403, "You do not have permission to perform this action.")

    def delete_observed_property(self, observed_property_id: str) -> None:
        raise HttpError(403, "You do not have permission to perform this action.")
