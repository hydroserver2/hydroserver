import uuid
from typing import Optional, ClassVar, TYPE_CHECKING
from pydantic import Field
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class Sensor(HydroServerBaseModel):
    name: str = Field(..., max_length=255)
    description: str
    encoding_type: str = Field(..., max_length=255)
    manufacturer: Optional[str] = Field(None, max_length=255)
    sensor_model: Optional[str] = Field(None, max_length=255, alias="model")
    sensor_model_link: Optional[str] = Field(None, max_length=500, alias="modelLink")
    method_type: str = Field(..., max_length=100)
    method_link: Optional[str] = Field(None, max_length=500)
    method_code: Optional[str] = Field(None, max_length=50)
    workspace_id: Optional[uuid.UUID] = None

    _editable_fields: ClassVar[set[str]] = {
        "name", "description", "encoding_type", "manufacturer", "sensor_model", "sensor_model_link", "method_type",
        "method_link", "method_code"
    }

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.sensors, **data)

        self._workspace = None

    @classmethod
    def get_route(cls):
        return "sensors"

    @property
    def workspace(self) -> Optional["Workspace"]:
        """The workspace this sensor belongs to."""

        if self._workspace is None and self.workspace_id:
            self._workspace = self.client.workspaces.get(uid=self.workspace_id)

        return self._workspace
