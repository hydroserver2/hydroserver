import uuid
from typing import Type, List, Dict, Any, Optional, ClassVar, TYPE_CHECKING
from requests import Response
from dataclasses import dataclass, field
from pydantic import BaseModel, ConfigDict, PrivateAttr, Field
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.services.base import HydroServerBaseService


class HydroServerBaseModel(BaseModel):
    uid: Optional[uuid.UUID] = Field(..., alias="id")

    _client: "HydroServer" = PrivateAttr()
    _service: "HydroServerBaseService" = PrivateAttr()
    _server_data: Dict[str, Any] = PrivateAttr()
    _editable_fields: ClassVar[set[str]] = set()

    def __init__(self, *, client: "HydroServer", service: Optional["HydroServerBaseService"] = None, **data):
        super().__init__(**data)

        self._client = client
        self._service = service
        self._server_data = self.dict(by_alias=False).copy()

    @classmethod
    def get_route(cls):
        raise NotImplementedError("Route not defined")

    @property
    def client(self) -> "HydroServer":
        return self._client

    @property
    def service(self) -> Any:
        return self._service

    @property
    def unsaved_changes(self) -> dict:
        return {
            k: v for k, v in self.__dict__.items()
            if k in self._editable_fields and k in self._server_data and v != self._server_data[k]
        }

    def save(self):
        """Saves changes to this resource to HydroServer."""

        if not self.service:
            raise NotImplementedError("Saving not enabled for this object.")

        if not self.uid:
            raise AttributeError("Data cannot be saved: UID is not set.")

        if self.unsaved_changes:
            saved_resource = self.service.update(
                self.uid, **self.unsaved_changes
            )
            self._server_data = saved_resource.dict(by_alias=False).copy()
            self.__dict__.update(saved_resource.__dict__)

    def refresh(self):
        """Refreshes this resource from HydroServer."""

        if not self.service:
            raise NotImplementedError("Refreshing not enabled for this object.")

        if self.uid is None:
            raise ValueError("Cannot refresh data without a valid ID.")

        refreshed_resource = self.service.get(self.uid)
        self._server_data = refreshed_resource.dict(by_alias=False).copy()
        self.__dict__.update(refreshed_resource.__dict__)

    def delete(self):
        """Deletes this resource from HydroServer."""

        if not self.service:
            raise NotImplementedError("Deleting not enabled for this object.")

        if self.uid is None:
            raise AttributeError("Cannot delete data without a valid ID.")

        self.service.delete(self.uid)
        self.uid = None

    model_config = ConfigDict(
        validate_assignment=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        alias_generator=to_camel,
    )


@dataclass
class HydroServerCollection:
    items: List["HydroServerBaseModel"]
    filters: Optional[dict[str, Any]] = None
    order_by: Optional[List[str]] = None
    offset: Optional[int] = None
    limit: Optional[int] = None
    total_count: Optional[int] = None

    _service: Optional[Any] = field(init=False, repr=False)

    def __init__(
        self,
        model: Type["HydroServerBaseModel"],
        client: "HydroServer",
        service: Optional[Any] = None,
        response: Optional[Response] = None,
        **data
    ):
        self._service = service

        self.filters = data.get("filters")
        self.order_by = data.get("order_by")

        payload = response.json() if response is not None else {}
        meta = payload.get("meta", {}) if isinstance(payload, dict) else {}

        self.offset = self._resolve_int_metadata("offset", meta, data)
        self.limit = self._resolve_int_metadata("limit", meta, data)
        self.total_count = self._resolve_int_metadata("total_count", meta, data, meta_key="totalCount")

        if "items" in data:
            self.items = data["items"]
        elif response is not None:
            self.items = [model(client=client, **entity) for entity in payload.get("data", [])]
        else:
            self.items = []

    @staticmethod
    def _resolve_int_metadata(
        field_name: str,
        meta: dict,
        data: dict,
        meta_key: Optional[str] = None,
    ) -> Optional[int]:
        field_value = data.get(field_name)
        if field_value is not None:
            return int(field_value)

        meta_value = meta.get(meta_key or field_name)
        if meta_value is not None:
            return int(meta_value)

        return None

    @property
    def service(self) -> "HydroServerBaseService":
        return self._service

    def next_page(self):
        """Fetches the next page of data from HydroServer."""

        if not self._service:
            raise NotImplementedError("Pagination not enabled for this collection.")

        limit = self.limit or 100

        return self._service.list(
            **(self.filters or {}),
            offset=(self.offset or 0) + limit,
            limit=limit,
            order_by=self.order_by or ...
        )

    def previous_page(self):
        """Fetches the previous page of data from HydroServer."""

        if not self._service:
            raise NotImplementedError("Pagination not enabled for this collection.")

        if not self.offset:
            return None

        limit = self.limit or 100

        return self._service.list(
            **(self.filters or {}),
            offset=max(0, self.offset - limit),
            limit=limit,
            order_by=self.order_by or ...
        )

    def fetch_all(self) -> "HydroServerCollection":
        """Fetches all pages of data from HydroServer for this collection."""

        if not self._service:
            raise NotImplementedError("Pagination not enabled for this collection.")

        all_items = list(self.items)
        limit = self.limit or 100
        total_count = self.total_count
        next_offset = (self.offset or 0) + len(self.items)

        while total_count is None or next_offset < total_count:
            page = self._service.list(
                **(self.filters or {}),
                offset=next_offset,
                limit=limit,
                order_by=self.order_by or ...
            )
            if not page.items:
                break
            all_items.extend(page.items)

            if page.total_count is not None:
                total_count = page.total_count

            next_offset += len(page.items)

        return self.__class__(
            model=type(self.items[0]) if self.items else None,
            client=self.items[0].client if self.items else None,
            service=self._service,
            items=all_items,
            filters=self.filters,
            order_by=self.order_by,
            offset=0,
            limit=len(all_items),
            total_count=len(all_items) if total_count is None else total_count,
        )
