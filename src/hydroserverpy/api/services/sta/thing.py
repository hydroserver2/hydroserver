import json
from typing import TYPE_CHECKING, Union, IO, List, Dict, Optional, Tuple
from uuid import UUID
from hydroserverpy.api.models import Thing
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class ThingService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = Thing
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Union["Workspace", UUID, str] = ...,
        bbox: Tuple[float, float, float, float] = ...,
        state: str = ...,
        county: str = ...,
        country: str = ...,
        site_type: str = ...,
        sampling_feature_type: str = ...,
        sampling_feature_code: str = ...,
        tag: Tuple[str, str] = ...,
        is_private: bool = ...,
        fetch_all: bool = False,
    ) -> List["Thing"]:
        """Fetch a collection of things."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            workspace_id=normalize_uuid(workspace),
            bbox=",".join([str(i) for i in bbox]) if bbox is not ... else bbox,
            state=state,
            county=county,
            country=country,
            site_type=site_type,
            sampling_feature_type=sampling_feature_type,
            sampling_feature_code=sampling_feature_code,
            tag=[f"{tag[0]}:{tag[1]}"] if tag is not ... else tag,
            is_private=is_private,
            fetch_all=fetch_all,
        )

    def create(
        self,
        workspace: Union["Workspace", UUID, str],
        name: str,
        description: str,
        sampling_feature_type: str,
        sampling_feature_code: str,
        site_type: str,
        is_private: False,
        latitude: float,
        longitude: float,
        elevation_m: Optional[float] = None,
        elevation_datum: Optional[str] = None,
        state: Optional[str] = None,
        county: Optional[str] = None,
        country: Optional[str] = None,
        data_disclaimer: Optional[str] = None,
        uid: Optional[UUID] = None,
    ) -> "Thing":
        """Create a new thing."""

        body = {
            "id": normalize_uuid(uid),
            "name": name,
            "description": description,
            "samplingFeatureType": sampling_feature_type,
            "samplingFeatureCode": sampling_feature_code,
            "siteType": site_type,
            "isPrivate": is_private,
            "dataDisclaimer": data_disclaimer,
            "workspaceId": normalize_uuid(workspace),
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "elevation_m": elevation_m,
                "elevationDatum": elevation_datum,
                "state": state,
                "county": county,
                "country": country,
            }
        }

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        name: str = ...,
        description: str = ...,
        sampling_feature_type: str = ...,
        sampling_feature_code: str = ...,
        site_type: str = ...,
        is_private: bool = ...,
        latitude: float = ...,
        longitude: float = ...,
        elevation_m: Optional[float] = ...,
        elevation_datum: Optional[str] = ...,
        state: Optional[str] = ...,
        county: Optional[str] = ...,
        country: Optional[str] = ...,
        data_disclaimer: Optional[str] = ...,
    ) -> "Thing":
        """Update a thing."""

        body = {
            "name": name,
            "description": description,
            "samplingFeatureType": sampling_feature_type,
            "samplingFeatureCode": sampling_feature_code,
            "siteType": site_type,
            "isPrivate": is_private,
            "dataDisclaimer": data_disclaimer,
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "elevation_m": elevation_m,
                "elevationDatum": elevation_datum,
                "state": state,
                "county": county,
                "country": country,
            }
        }

        return super().update(uid=str(uid), **body)

    def add_tag(self, uid: Union[UUID, str], key: str, value: str) -> Dict[str, str]:
        """Tag a HydroServer thing."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/tags"
        headers = {"Content-type": "application/json"}
        body = {
            "key": key,
            "value": value
        }
        return self.client.request(
            "post", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        ).json()

    def update_tag(self, uid: Union[UUID, str], key: str, value: str) -> Dict[str, str]:
        """Update the tag of a HydroServer thing."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/tags"
        headers = {"Content-type": "application/json"}
        body = {
            "key": key,
            "value": value
        }
        return self.client.request(
            "put", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        ).json()

    def delete_tag(self, uid: Union[UUID, str], key: str, value: str) -> None:
        """Remove a tag from a HydroServer thing."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/tags"
        headers = {"Content-type": "application/json"}
        body = {
            "key": key,
            "value": value
        }
        self.client.request(
            "delete", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        )

    def add_file_attachment(self, uid: Union[UUID, str], file: IO[bytes], file_attachment_type: str) -> Dict[str, str]:
        """Add a file attachment of a HydroServer thing."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/file-attachments"

        return self.client.request(
            "post", path, data={"file_attachment_type": file_attachment_type}, files={"file": file}
        ).json()

    def delete_file_attachment(self, uid: Union[UUID, str], name: str) -> None:
        """Delete a file attachment of a HydroServer thing."""

        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}/file-attachments"
        headers = {"Content-type": "application/json"}
        body = {
            "name": name
        }
        self.client.request(
            "delete", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        )
