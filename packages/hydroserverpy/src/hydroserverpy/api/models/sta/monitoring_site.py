import uuid
from typing import Optional, ClassVar, List, Dict, IO, TYPE_CHECKING
from pydantic import Field, field_validator
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace, Datastream


class MonitoringSite(HydroServerBaseModel):
    name: str = Field(..., max_length=200)
    description: str
    code: str = Field(..., max_length=200)
    type: str = Field(..., max_length=200)
    data_disclaimer: Optional[str] = None
    is_private: bool
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    elevation_m: Optional[float] = Field(
        None, ge=-99999, le=99999, alias="elevation_m"
    )
    elevation_datum: Optional[str] = Field(
        None, max_length=255
    )
    admin_area_1: Optional[str] = Field(None, max_length=200)
    admin_area_2: Optional[str] = Field(None, max_length=200)
    country: Optional[str] = Field(None, max_length=2)
    tags: Dict[str, str]
    file_attachments: Dict[str, Dict[str, str]]
    workspace_id: uuid.UUID

    _editable_fields: ClassVar[set[str]] = {
        "name", "description", "code", "type", "data_disclaimer",
        "is_private", "latitude", "longitude", "elevation_m", "elevation_datum", "admin_area_1", "admin_area_2",
        "country"
    }

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.monitoring_sites, **data)

        self._workspace = None
        self._datastreams = None

    @classmethod
    def get_route(cls):
        return "monitoring-sites"

    @property
    def workspace(self) -> "Workspace":
        """The workspace this monitoring site belongs to."""

        if self._workspace is None:
            self._workspace = self.client.workspaces.get(uid=self.workspace_id)

        return self._workspace

    @property
    def datastreams(self) -> List["Datastream"]:
        """The datastreams collected at this monitoring site."""

        if self._datastreams is None:
            self._datastreams = self.client.datastreams.list(monitoring_site=self.uid, fetch_all=True).items

        return self._datastreams

    @field_validator("tags", mode="before")
    def transform_tags(cls, v):
        if isinstance(v, list):
            return {item["key"]: item["value"] for item in v if "key" in item and "value" in item}
        return v

    @field_validator("file_attachments", mode="before")
    def transform_file_attachments(cls, v):
        if isinstance(v, list):
            return {
                item["name"]: {
                    "link": item["link"],
                    "file_attachment_type": item["fileAttachmentType"],
                } for item in v if "name" in item and "link" in item
            }
        return v

    def add_tag(self, key: str, value: str):
        """Add a tag to this monitoring site."""

        self.client.monitoring_sites.add_tag(uid=self.uid, key=key, value=value)
        self.tags[key] = value

    def update_tag(self, key: str, value: str):
        """Edit a tag of this monitoring site."""

        self.client.monitoring_sites.update_tag(uid=self.uid, key=key, value=value)
        self.tags[key] = value

    def delete_tag(self, key: str):
        """Delete a tag of this monitoring site."""

        self.client.monitoring_sites.delete_tag(uid=self.uid, key=key, value=self.tags[key])
        del self.tags[key]

    def add_file_attachment(self, file: IO[bytes], file_attachment_type: str):
        """Add a file attachment for this monitoring site."""

        file_attachment = self.client.monitoring_sites.add_file_attachment(
            uid=self.uid, file=file, file_attachment_type=file_attachment_type
        )
        self.file_attachments[file_attachment["name"]] = {
            "link": file_attachment["link"],
            "file_attachment_type": file_attachment_type,
        }

    def delete_file_attachment(self, name: str):
        """Delete a file attachment of this monitoring site."""

        self.client.monitoring_sites.delete_file_attachment(uid=self.uid, name=name)
        del self.file_attachments[name]
