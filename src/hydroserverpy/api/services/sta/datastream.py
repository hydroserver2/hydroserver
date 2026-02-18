import json
import pandas as pd
from typing import Union, Optional, Literal, List, Dict, Tuple, IO, TYPE_CHECKING
from uuid import UUID
from datetime import datetime
from pydantic.alias_generators import to_camel
from hydroserverpy.api.models import Datastream, ObservationCollection
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import (
        Workspace,
        Thing,
        Unit,
        Sensor,
        ObservedProperty,
        ProcessingLevel,
    )


class DatastreamService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = Datastream
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Union["Workspace", UUID, str] = ...,
        thing: Union["Thing", UUID, str] = ...,
        sensor: Union["Sensor", UUID, str] = ...,
        observed_property: Union["ObservedProperty", UUID, str] = ...,
        processing_level: Union["ProcessingLevel", UUID, str] = ...,
        unit: Union["Unit", UUID, str] = ...,
        observation_type: str = ...,
        sampled_medium: str = ...,
        status: Optional[str] = ...,
        result_type: str = ...,
        tag: Tuple[str, str] = ...,
        is_private: bool = ...,
        value_count_max: int = ...,
        value_count_min: int = ...,
        phenomenon_begin_time_max: datetime = ...,
        phenomenon_begin_time_min: datetime = ...,
        phenomenon_end_time_max: datetime = ...,
        phenomenon_end_time_min: datetime = ...,
        result_begin_time_max: datetime = ...,
        result_begin_time_min: datetime = ...,
        result_end_time_max: datetime = ...,
        result_end_time_min: datetime = ...,
        fetch_all: bool = False,
    ) -> List["Workspace"]:
        """Fetch a collection of HydroServer workspaces."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            workspace_id=normalize_uuid(workspace),
            thing_id=normalize_uuid(thing),
            sensor_id=normalize_uuid(sensor),
            observed_property_id=normalize_uuid(observed_property),
            processing_level_id=normalize_uuid(processing_level),
            unit_id=normalize_uuid(unit),
            observation_type=observation_type,
            sampled_medium=sampled_medium,
            status=status,
            result_type=result_type,
            tag=[f"{tag[0]}:{tag[1]}"] if tag is not ... else tag,
            is_private=is_private,
            value_count_max=value_count_max,
            value_count_min=value_count_min,
            phenomenon_begin_time_max=phenomenon_begin_time_max,
            phenomenon_begin_time_min=phenomenon_begin_time_min,
            phenomenon_end_time_max=phenomenon_end_time_max,
            phenomenon_end_time_min=phenomenon_end_time_min,
            result_begin_time_max=result_begin_time_max,
            result_begin_time_min=result_begin_time_min,
            result_end_time_max=result_end_time_max,
            result_end_time_min=result_end_time_min,
            fetch_all=fetch_all,
        )

    def create(
        self,
        name: str,
        description: str,
        thing: Union["Thing", UUID, str],
        sensor: Union["Sensor", UUID, str],
        observed_property: Union["ObservedProperty", UUID, str],
        processing_level: Union["ProcessingLevel", UUID, str],
        unit: Union["Unit", UUID, str],
        observation_type: str,
        result_type: str,
        sampled_medium: str,
        no_data_value: float,
        aggregation_statistic: str,
        time_aggregation_interval: float,
        time_aggregation_interval_unit: Literal["seconds", "minutes", "hours", "days"],
        intended_time_spacing: Optional[float] = None,
        intended_time_spacing_unit: Optional[
            Literal["seconds", "minutes", "hours", "days"]
        ] = None,
        status: Optional[str] = None,
        value_count: Optional[int] = None,
        phenomenon_begin_time: Optional[datetime] = None,
        phenomenon_end_time: Optional[datetime] = None,
        result_begin_time: Optional[datetime] = None,
        result_end_time: Optional[datetime] = None,
        is_private: bool = False,
        is_visible: bool = True,
        uid: Optional[UUID] = None,
    ) -> "Datastream":
        """Create a new datastream."""

        body = {
            "id": normalize_uuid(uid),
            "name": name,
            "description": description,
            "thingId": normalize_uuid(thing),
            "sensorId": normalize_uuid(sensor),
            "observedPropertyId": normalize_uuid(observed_property),
            "processingLevelId": normalize_uuid(processing_level),
            "unitId": normalize_uuid(unit),
            "observationType": observation_type,
            "resultType": result_type,
            "sampledMedium": sampled_medium,
            "noDataValue": no_data_value,
            "aggregationStatistic": aggregation_statistic,
            "timeAggregationInterval": time_aggregation_interval,
            "timeAggregationIntervalUnit": time_aggregation_interval_unit,
            "intendedTimeSpacing": intended_time_spacing,
            "intendedTimeSpacingUnit": intended_time_spacing_unit,
            "status": status,
            "valueCount": value_count,
            "phenomenonBeginTime": phenomenon_begin_time,
            "phenomenonEndTime": phenomenon_end_time,
            "resultBeginTime": result_begin_time,
            "resultEndTime": result_end_time,
            "isPrivate": is_private,
            "isVisible": is_visible,
        }

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        name: str = ...,
        description: str = ...,
        thing: Union["Thing", UUID, str] = ...,
        thing_id: UUID = ...,
        sensor: Union["Sensor", UUID, str] = ...,
        sensor_id: UUID = ...,
        observed_property: Union["ObservedProperty", UUID, str] = ...,
        observed_property_id: UUID = ...,
        processing_level: Union["ProcessingLevel", UUID, str] = ...,
        processing_level_id: UUID = ...,
        unit: Union["Unit", UUID, str] = ...,
        unit_id: UUID = ...,
        observation_type: str = ...,
        result_type: str = ...,
        sampled_medium: str = ...,
        no_data_value: float = ...,
        aggregation_statistic: str = ...,
        time_aggregation_interval: float = ...,
        time_aggregation_interval_unit: Literal[
            "seconds", "minutes", "hours", "days"
        ] = ...,
        intended_time_spacing: Optional[float] = ...,
        intended_time_spacing_unit: Optional[
            Literal["seconds", "minutes", "hours", "days"]
        ] = ...,
        status: Optional[str] = ...,
        value_count: Optional[int] = ...,
        phenomenon_begin_time: Optional[datetime] = ...,
        phenomenon_end_time: Optional[datetime] = ...,
        result_begin_time: Optional[datetime] = ...,
        result_end_time: Optional[datetime] = ...,
        is_private: bool = ...,
        is_visible: bool = ...,
    ) -> "Datastream":
        """Update a datastream."""

        body = {
            "name": name,
            "description": description,
            "thingId": normalize_uuid(thing if thing is not ... else thing_id),
            "sensorId": normalize_uuid(sensor if sensor is not ... else sensor_id),
            "observedPropertyId": normalize_uuid(
                observed_property if observed_property is not ... else observed_property_id
            ),
            "processingLevelId": normalize_uuid(
                processing_level if processing_level is not ... else processing_level_id
            ),
            "unitId": normalize_uuid(unit if unit is not ... else unit_id),
            "observationType": observation_type,
            "resultType": result_type,
            "sampledMedium": sampled_medium,
            "noDataValue": no_data_value,
            "aggregationStatistic": aggregation_statistic,
            "timeAggregationInterval": time_aggregation_interval,
            "timeAggregationIntervalUnit": time_aggregation_interval_unit,
            "intendedTimeSpacing": intended_time_spacing,
            "intendedTimeSpacingUnit": intended_time_spacing_unit,
            "status": status,
            "valueCount": value_count,
            "phenomenonBeginTime": phenomenon_begin_time,
            "phenomenonEndTime": phenomenon_end_time,
            "resultBeginTime": result_begin_time,
            "resultEndTime": result_end_time,
            "isPrivate": is_private,
            "isVisible": is_visible,
        }

        return super().update(uid=str(uid), **body)

    def get_observations(
        self,
        uid: Union[UUID, str],
        page: int = ...,
        page_size: int = 100000,
        order_by: List[str] = ...,
        phenomenon_time_max: datetime = ...,
        phenomenon_time_min: datetime = ...,
        result_qualifier_code: str = ...,
        fetch_all: bool = False,
    ) -> ObservationCollection:
        """Retrieve observations of a datastream."""

        params = {
            "page": page,
            "page_size": page_size,
            "order_by": ",".join(order_by) if order_by is not ... else order_by,
            "phenomenon_time_max": phenomenon_time_max,
            "phenomenon_time_min": phenomenon_time_min,
            "result_qualifier_code": result_qualifier_code,
            "format": "column"
        }
        params = {
            k: ("null" if v is None else v)
            for k, v in params.items()
            if v is not ...
        }

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/observations"
        response = self.client.request("get", path, params=params)
        datastream = self.get(uid=uid)
        collection = ObservationCollection(
            datastream=datastream,
            response=response,
            order_by=params.get("order_by"),
            filters={k: v for k, v in params.items() if k not in ["page", "page_size", "order_by", "format"]},
        )
        if fetch_all is True:
            collection = collection.fetch_all()

        return collection

    def load_observations(
        self,
        uid: Union[UUID, str],
        observations: pd.DataFrame,
        mode: str = "insert"
    ) -> None:
        """Load observations to a datastream."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/observations/bulk-create"
        headers = {"Content-type": "application/json"}
        params = {"mode": mode}
        body = {
            "fields": [to_camel(col) for col in observations.columns.tolist()],
            "data": observations.values.tolist()
        }

        self.client.request(
            "post", path, headers=headers, params=params, data=json.dumps(body, default=self.default_serializer)
        )

    def delete_observations(
        self,
        uid: Union[UUID, str],
        phenomenon_time_start: Optional[datetime] = None,
        phenomenon_time_end: Optional[datetime] = None,
    ) -> None:
        """Delete observations from a datastream."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/observations/bulk-delete"
        headers = {"Content-type": "application/json"}
        body = {}

        if phenomenon_time_start is not None:
            body["phenomenonTimeStart"] = phenomenon_time_start
        if phenomenon_time_end is not None:
            body["phenomenonTimeEnd"] = phenomenon_time_end

        self.client.request(
            "post", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        )

    def add_tag(self, uid: Union[UUID, str], key: str, value: str) -> Dict[str, str]:
        """Tag a HydroServer datastream."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/tags"
        headers = {"Content-type": "application/json"}
        body = {
            "key": key,
            "value": value
        }
        return self.client.request(
            "post", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        ).json()

    def update_tag(self, uid: Union[UUID, str], key: str, value: str) -> Dict[str, str]:
        """Update the tag of a HydroServer datastream."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/tags"
        headers = {"Content-type": "application/json"}
        body = {
            "key": key,
            "value": value
        }
        return self.client.request(
            "put", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        ).json()

    def delete_tag(self, uid: Union[UUID, str], key: str, value: str) -> None:
        """Remove a tag from a HydroServer datastream."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/tags"
        headers = {"Content-type": "application/json"}
        body = {
            "key": key,
            "value": value
        }
        self.client.request(
            "delete", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        )

    def add_file_attachment(self, uid: Union[UUID, str], file: IO[bytes], file_attachment_type: str) -> Dict[str, str]:
        """Add a file attachment of a HydroServer datastream."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/file-attachments"

        return self.client.request(
            "post", path, data={"file_attachment_type": file_attachment_type}, files={"file": file}
        ).json()

    def delete_file_attachment(self, uid: Union[UUID, str], name: str) -> None:
        """Delete a file attachment of a HydroServer datastream."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/file-attachments"
        headers = {"Content-type": "application/json"}
        body = {
            "name": name
        }
        self.client.request(
            "delete", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        )
