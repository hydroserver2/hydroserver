import uuid
from typing import Optional, ClassVar, TYPE_CHECKING
from pydantic import Field
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class Method(HydroServerBaseModel):
    name: str = Field(..., max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    type: str = Field(..., max_length=100)
    description: str
    definition: Optional[str] = Field(None, max_length=500)
    sensor_model: Optional[str] = Field(None, max_length=255)
    sensor_model_manufacturer: Optional[str] = Field(None, max_length=255)
    sensor_model_definition: Optional[str] = Field(None, max_length=500)
    workspace_id: Optional[uuid.UUID] = None

    _editable_fields: ClassVar[set[str]] = {
        "name",
        "code",
        "type",
        "description",
        "definition",
        "sensor_model",
        "sensor_model_manufacturer",
        "sensor_model_definition",
    }

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.methods, **data)

        self._workspace = None

    @classmethod
    def get_route(cls):
        return "methods"

    @property
    def workspace(self) -> Optional["Workspace"]:
        """The workspace this method belongs to."""

        if self._workspace is None and self.workspace_id:
            self._workspace = self.client.workspaces.get(uid=self.workspace_id)

        return self._workspace
