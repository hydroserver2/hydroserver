import uuid
from typing import Optional, ClassVar, TYPE_CHECKING
from pydantic import Field
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class ObservedProperty(HydroServerBaseModel):
    name: str = Field(..., max_length=255)
    definition: str
    description: str
    observed_property_type: str = Field(..., max_length=255, alias="type")
    code: str = Field(..., max_length=255)
    workspace_id: Optional[uuid.UUID] = None

    _editable_fields: ClassVar[set[str]] = {"name", "definition", "description", "observed_property_type", "code"}

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.observedproperties, **data)

        self._workspace = None

    @classmethod
    def get_route(cls):
        return "observed-properties"

    @property
    def workspace(self) -> Optional["Workspace"]:
        """The workspace this observed property belongs to."""

        if self._workspace is None and self.workspace_id:
            self._workspace = self.client.workspaces.get(uid=self.workspace_id)

        return self._workspace
