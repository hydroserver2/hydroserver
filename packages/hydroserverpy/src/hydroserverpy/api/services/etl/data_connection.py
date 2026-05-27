from typing import List, Literal, Optional, Union, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models.etl.data_connection import DataConnection
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class DataConnectionService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = DataConnection
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        workspace: Optional[Union[UUID, str]] = ...,
        payload_type: str = ...,
        fetch_all: bool = False,
    ) -> List[DataConnection]:
        """Fetch a collection of ETL data connections."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            fetch_all=fetch_all,
            workspace_id=normalize_uuid(workspace),
            payload_type=payload_type,
        )

    def create(
        self,
        name: str,
        workspace: Union[UUID, str],
        source_url: str,
        timestamp_key: str,
        payload_type: Literal["CSV", "JSON"],
        description: Optional[str] = None,
        timestamp_format: Optional[str] = None,
        timezone_type: Optional[Literal["offset", "iana"]] = None,
        timezone: Optional[str] = None,
        auth_header_name: Optional[str] = None,
        auth_header_value: Optional[str] = None,
        header_row: Optional[int] = None,
        data_start_row: Optional[int] = None,
        delimiter: Optional[str] = None,
        jmespath: Optional[str] = None,
        placeholder_variables: Optional[List[dict]] = None,
        notification: Optional[dict] = None,
        uid: Optional[UUID] = None,
    ) -> DataConnection:
        """Create a new ETL data connection."""

        payload: dict = {
            "type": payload_type,
            "timestampKey": timestamp_key,
            "timestampFormat": timestamp_format,
        }
        if payload_type == "CSV":
            if header_row is not None:
                payload["headerRow"] = header_row
            if data_start_row is not None:
                payload["dataStartRow"] = data_start_row
            if delimiter is not None:
                payload["delimiter"] = delimiter
        elif payload_type == "JSON":
            if jmespath is not None:
                payload["jmespath"] = jmespath

        body = {
            "name": name,
            "description": description,
            "sourceUrl": source_url,
            "workspaceId": normalize_uuid(workspace),
            "timezoneType": timezone_type,
            "timezone": timezone,
            "authHeaderName": auth_header_name,
            "authHeaderValue": auth_header_value,
            "payload": payload,
            "placeholderVariables": self._serialize_placeholder_variables(
                placeholder_variables or []
            ),
        }

        if uid is not None:
            body["id"] = normalize_uuid(uid)

        if notification is not None:
            body["notification"] = notification

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        name: str,
        source_url: str,
        timestamp_key: str,
        payload_type: Literal["CSV", "JSON"],
        description: Optional[str] = None,
        timestamp_format: Optional[str] = None,
        timezone_type: Optional[Literal["offset", "iana"]] = None,
        timezone: Optional[str] = None,
        auth_header_name: Optional[str] = None,
        auth_header_value: Optional[str] = None,
        header_row: Optional[int] = None,
        data_start_row: Optional[int] = None,
        delimiter: Optional[str] = None,
        jmespath: Optional[str] = None,
        placeholder_variables: Optional[List[dict]] = None,
        notification: Optional[dict] = ...,
    ) -> DataConnection:
        """Update an ETL data connection."""

        payload: dict = {
            "type": payload_type,
            "timestampKey": timestamp_key,
            "timestampFormat": timestamp_format,
        }
        if payload_type == "CSV":
            if header_row is not None:
                payload["headerRow"] = header_row
            if data_start_row is not None:
                payload["dataStartRow"] = data_start_row
            if delimiter is not None:
                payload["delimiter"] = delimiter
        elif payload_type == "JSON":
            if jmespath is not None:
                payload["jmespath"] = jmespath

        body = {
            "name": name,
            "description": description,
            "sourceUrl": source_url,
            "timezoneType": timezone_type,
            "timezone": timezone,
            "authHeaderName": auth_header_name,
            "authHeaderValue": auth_header_value,
            "payload": payload,
            "placeholderVariables": self._serialize_placeholder_variables(
                placeholder_variables or []
            ),
        }

        if notification is not ...:
            body["notification"] = notification

        return super().update(uid=str(uid), **body)

    @staticmethod
    def _serialize_placeholder_variables(variables: List[dict]) -> List[dict]:
        result = []
        for pv in variables:
            item = {
                "name": pv["name"],
                "type": pv.get("variable_type") or pv.get("type"),
            }
            ts_format = pv.get("timestamp_format") or pv.get("timestampFormat")
            if ts_format is not None:
                item["timestampFormat"] = ts_format
            result.append(item)
        return result
