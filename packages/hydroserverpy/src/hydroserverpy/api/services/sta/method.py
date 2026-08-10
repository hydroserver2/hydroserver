from typing import Optional, Union, List, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models import Method
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace, MonitoringSite, Datastream


class MethodService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = Method
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Optional[Union["Workspace", UUID, str]] = ...,
        monitoring_site: Optional[Union["MonitoringSite", UUID, str]] = ...,
        datastream: Optional[Union["Datastream", UUID, str]] = ...,
        type: str = ...,
        sensor_model: Optional[str] = ...,
        sensor_model_manufacturer: Optional[str] = ...,
        fetch_all: bool = False,
    ) -> List["Method"]:
        """Fetch a collection of methods."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            workspace_id=normalize_uuid(workspace),
            monitoring_site_id=normalize_uuid(monitoring_site),
            datastream_id=normalize_uuid(datastream),
            type=type,
            sensor_model=sensor_model,
            sensor_model_manufacturer=sensor_model_manufacturer,
            fetch_all=fetch_all,
        )

    def create(
        self,
        name: str,
        description: str,
        type: str,
        code: Optional[str] = None,
        definition: Optional[str] = None,
        sensor_model: Optional[str] = None,
        sensor_model_manufacturer: Optional[str] = None,
        sensor_model_definition: Optional[str] = None,
        workspace: Optional[Union["Workspace", UUID, str]] = None,
        uid: Optional[UUID] = None,
    ) -> "Method":
        """Create a new method."""

        body = {
            "id": normalize_uuid(uid),
            "name": name,
            "description": description,
            "code": code,
            "type": type,
            "definition": definition,
            "sensorModel": sensor_model,
            "sensorModelManufacturer": sensor_model_manufacturer,
            "sensorModelDefinition": sensor_model_definition,
            "workspaceId": normalize_uuid(workspace),
        }

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        name: str = ...,
        description: str = ...,
        type: str = ...,
        code: Optional[str] = ...,
        definition: Optional[str] = ...,
        sensor_model: Optional[str] = ...,
        sensor_model_manufacturer: Optional[str] = ...,
        sensor_model_definition: Optional[str] = ...,
    ) -> "Method":
        """Update a method."""

        body = {
            "name": name,
            "description": description,
            "code": code,
            "type": type,
            "definition": definition,
            "sensorModel": sensor_model,
            "sensorModelManufacturer": sensor_model_manufacturer,
            "sensorModelDefinition": sensor_model_definition,
        }

        return super().update(uid=str(uid), **body)
