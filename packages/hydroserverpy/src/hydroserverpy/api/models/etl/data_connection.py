import uuid
from typing import ClassVar, List, Optional, TYPE_CHECKING
from pydantic import Field, AliasPath, AliasChoices
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace, Task


class DataConnection(HydroServerBaseModel):
    name: str = Field(..., max_length=255)
    data_connection_type: str = Field(..., max_length=255, alias="type")
    workspace_id: Optional[uuid.UUID] = Field(
        None, validation_alias=AliasChoices("workspaceId", AliasPath("workspace", "id"))
    )
    extractor_type: str = Field(..., max_length=255, validation_alias=AliasPath("extractor", "type"))
    extractor_settings: dict = Field(default_factory=dict, validation_alias=AliasPath("extractor", "settings"))
    transformer_type: str = Field(..., max_length=255, validation_alias=AliasPath("transformer", "type"))
    transformer_settings: dict = Field(default_factory=dict, validation_alias=AliasPath("transformer", "settings"))
    loader_type: str = Field(..., max_length=255, validation_alias=AliasPath("loader", "type"))
    loader_settings: dict = Field(default_factory=dict, validation_alias=AliasPath("loader", "settings"))

    _editable_fields: ClassVar[set[str]] = {
        "name",
        "data_connection_type",
        "extractor_type",
        "extractor_settings",
        "transformer_type",
        "transformer_settings",
        "loader_type",
        "loader_settings",
    }

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.dataconnections, **data)

        self._workspace = None
        self._tasks = None

    @classmethod
    def get_route(cls):
        return "etl-data-connections"

    @property
    def workspace(self) -> "Workspace":
        """The workspace this ETL data connection belongs to."""

        if self._workspace is None and self.workspace_id:
            self._workspace = self.client.workspaces.get(uid=self.workspace_id)

        return self._workspace

    @property
    def tasks(self) -> List["Task"]:
        """The ETL tasks associated with this ETL data connection."""

        if self._tasks is None:
            self._tasks = self.client.tasks.list(
                data_connection=self.uid, fetch_all=True
            ).items

        return self._tasks
