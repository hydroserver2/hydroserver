import uuid
from typing import Optional, ClassVar, TYPE_CHECKING
from pydantic import Field
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class Unit(HydroServerBaseModel):
    name: str = Field(..., max_length=255)
    symbol: str = Field(..., max_length=255)
    definition: str
    unit_type: str = Field(..., max_length=255, alias="type")
    workspace_id: Optional[uuid.UUID] = None

    _editable_fields: ClassVar[set[str]] = {"name", "symbol", "definition", "unit_type"}

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.units, **data)

        self._workspace = None

    @classmethod
    def get_route(cls):
        return "units"

    @property
    def workspace(self) -> Optional["Workspace"]:
        """The workspace this unit belongs to."""

        if self._workspace is None and self.workspace_id:
            self._workspace = self.client.workspaces.get(uid=self.workspace_id)

        return self._workspace
