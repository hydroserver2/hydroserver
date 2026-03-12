import uuid
from typing import ClassVar, List, Optional, TYPE_CHECKING
from pydantic import Field
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace, Task


class OrchestrationSystem(HydroServerBaseModel):
    name: str = Field(..., max_length=255)
    orchestration_system_type: str = Field(..., max_length=255, alias="type")
    workspace_id: Optional[uuid.UUID] = None

    _editable_fields: ClassVar[set[str]] = {"name", "orchestration_system_type"}

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.orchestrationsystems, **data)

        self._workspace = None
        self._tasks = None

    @classmethod
    def get_route(cls):
        return "etl-orchestration-systems"

    @property
    def workspace(self) -> "Workspace":
        """The workspace this orchestration system belongs to."""

        if self._workspace is None and self.workspace_id:
            self._workspace = self.client.workspaces.get(uid=self.workspace_id)

        return self._workspace

    @property
    def tasks(self) -> List["Task"]:
        """The ETL tasks associated with this orchestration system."""

        if self._tasks is None:
            self._tasks = self.client.tasks.list(
                orchestration_system=self.uid, fetch_all=True
            ).items

        return self._tasks
