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
    linked_resources: Dict[str, Dict[str, str]]
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

    @field_validator("linked_resources", mode="before")
    def transform_linked_resources(cls, v):
        if isinstance(v, list):
            return {
                item["name"]: {
                    "id": item["id"],
                    "link": item["link"],
                    "type": item["type"],
                } for item in v if "name" in item and "link" in item
            }
        return v

    def set_tag(self, key: str, value: str):
        """Create or update a tag on this monitoring site."""

        self.client.monitoring_sites.set_tag(uid=self.uid, key=key, value=value)
        self.tags[key] = value

    def delete_tag(self, key: str):
        """Delete a tag of this monitoring site."""

        self.client.monitoring_sites.delete_tag(uid=self.uid, key=key)
        self.tags.pop(key, None)

    def add_linked_resource(
        self,
        name: str,
        type: str,
        file: Optional[IO[bytes]] = None,
        url: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """
        Add a linked resource to this monitoring site. Exactly one of `file`/`url` must be
        given — whichever one is provided determines whether the resource is hosted by
        HydroServer or an external link.
        """

        linked_resource = self.client.monitoring_sites.add_linked_resource(
            uid=self.uid, name=name, type=type, file=file, url=url,
            description=description,
        )
        self.linked_resources[linked_resource["name"]] = {
            "id": linked_resource["id"],
            "link": linked_resource["link"],
            "type": type,
        }

    def delete_linked_resource(self, name: str):
        """Delete a linked resource of this monitoring site."""

        linked_resource_id = self.linked_resources[name]["id"]
        self.client.monitoring_sites.delete_linked_resource(uid=self.uid, linked_resource_id=linked_resource_id)
        del self.linked_resources[name]
