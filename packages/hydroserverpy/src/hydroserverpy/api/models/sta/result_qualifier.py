import uuid
from typing import Optional, ClassVar, TYPE_CHECKING
from pydantic import Field
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class ResultQualifier(HydroServerBaseModel):
    name: str = Field(..., max_length=255)
    description: str
    is_active: bool = True
    workspace_id: Optional[uuid.UUID] = None

    _editable_fields: ClassVar[set[str]] = {"name", "description", "is_active"}

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.resultqualifiers, **data)

        self._workspace = None

    @classmethod
    def get_route(cls):
        return "result-qualifiers"

    @property
    def workspace(self) -> Optional["Workspace"]:
        """The workspace this result qualifier belongs to."""

        if self._workspace is None and self.workspace_id:
            self._workspace = self.client.workspaces.get(uid=self.workspace_id)

        return self._workspace
