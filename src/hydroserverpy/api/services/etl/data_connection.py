from typing import Union, List, Optional, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models import DataConnection
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import Workspace


class DataConnectionService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = DataConnection
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Union["Workspace", UUID, str] = ...,
        data_connection_type: str = ...,
        extractor_type: str = ...,
        transformer_type: str = ...,
        loader_type: str = ...,
        fetch_all: bool = False,
    ) -> List["DataConnection"]:
        """Fetch a collection of ETL data connections."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            workspace_id=normalize_uuid(workspace),
            type=data_connection_type,
            extractor_type=extractor_type,
            transformer_type=transformer_type,
            loader_type=loader_type,
            fetch_all=fetch_all,
        )

    def create(
        self,
        name: str,
        data_connection_type: str,
        workspace: Optional[Union["Workspace", UUID, str]] = None,
        extractor_type: str = ...,
        extractor_settings: dict = ...,
        transformer_type: str = ...,
        transformer_settings: dict = ...,
        loader_type: str = ...,
        loader_settings: dict = ...,
        uid: Optional[UUID] = None
    ) -> "DataConnection":
        """Create a new data connection."""

        body = {
            "id": normalize_uuid(uid),
            "name": name,
            "type": data_connection_type,
            "workspaceId": normalize_uuid(workspace),
            "extractor": {
                "type": extractor_type,
                "settings": extractor_settings,
            },
            "transformer": {
                "type": transformer_type,
                "settings": transformer_settings,
            },
            "loader": {
                "type": loader_type,
                "settings": loader_settings,
            }
        }

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        name: str = ...,
        data_connection_type: str = ...,
        extractor_type: str = ...,
        extractor_settings: dict = ...,
        transformer_type: str = ...,
        transformer_settings: dict = ...,
        loader_type: str = ...,
        loader_settings: dict = ...,
    ) -> "DataConnection":
        """Update an ETL data connection."""

        body = {
            "name": name,
            "type": data_connection_type,
        }

        if extractor_type is not ... or extractor_settings is not ...:
            body["extractor"] = {
                "type": extractor_type,
                "settings": extractor_settings,
            }

        if transformer_type is not ... or transformer_settings is not ...:
            body["transformer"] = {
                "type": transformer_type,
                "settings": transformer_settings,
            }

        if loader_type is not ... or loader_settings is not ...:
            body["loader"] = {
                "type": loader_type,
                "settings": loader_settings,
            }

        return super().update(uid=str(uid), **body)
