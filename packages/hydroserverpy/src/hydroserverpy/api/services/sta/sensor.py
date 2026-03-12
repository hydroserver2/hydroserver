from typing import Optional, Union, List, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models import Sensor
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace, Thing, Datastream


class SensorService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = Sensor
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Optional[Union["Workspace", UUID, str]] = ...,
        thing: Optional[Union["Thing", UUID, str]] = ...,
        datastream: Optional[Union["Datastream", UUID, str]] = ...,
        encoding_type: str = ...,
        manufacturer: Optional[str] = ...,
        method_type: str = ...,
        fetch_all: bool = False,
    ) -> List["Sensor"]:
        """Fetch a collection of sensors."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            workspace_id=normalize_uuid(workspace),
            thing_id=normalize_uuid(thing),
            datastream_id=normalize_uuid(datastream),
            encoding_type=encoding_type,
            manufacturer=manufacturer,
            method_type=method_type,
            fetch_all=fetch_all,
        )

    def create(
        self,
        name: str,
        description: str,
        encoding_type: str,
        method_type: str,
        manufacturer: Optional[str] = None,
        sensor_model: Optional[str] = None,
        sensor_model_link: Optional[str] = None,
        method_link: Optional[str] = None,
        method_code: Optional[str] = None,
        workspace: Optional[Union["Workspace", UUID, str]] = None,
        uid: Optional[UUID] = None
    ) -> "Sensor":
        """Create a new sensor."""

        body = {
            "id": normalize_uuid(uid),
            "name": name,
            "description": description,
            "encodingType": encoding_type,
            "methodType": method_type,
            "manufacturer": manufacturer,
            "model": sensor_model,
            "modelLink": sensor_model_link,
            "methodLink": method_link,
            "methodCode": method_code,
            "workspaceId": normalize_uuid(workspace),
        }

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        name: str = ...,
        description: str = ...,
        encoding_type: str = ...,
        method_type: str = ...,
        manufacturer: Optional[str] = ...,
        sensor_model: Optional[str] = ...,
        sensor_model_link: Optional[str] = ...,
        method_link: Optional[str] = ...,
        method_code: Optional[str] = ...,
    ) -> "Sensor":
        """Update a sensor."""

        body = {
            "name": name,
            "description": description,
            "encodingType": encoding_type,
            "methodType": method_type,
            "manufacturer": manufacturer,
            "model": sensor_model,
            "modelLink": sensor_model_link,
            "methodLink": method_link,
            "methodCode": method_code,
        }

        return super().update(uid=str(uid), **body)
