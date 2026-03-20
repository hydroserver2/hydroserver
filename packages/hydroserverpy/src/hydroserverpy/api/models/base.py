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
    def service(self) -> "HydroServerBaseService":
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
    page: Optional[int] = None
    page_size: Optional[int] = None
    total_pages: Optional[int] = None
    total_count: Optional[int] = None

    _service: Optional["HydroServerBaseService"] = field(init=False, repr=False)

    def __init__(
        self,
        model: Type["HydroServerBaseModel"],
        client: "HydroServer",
        service: Optional["HydroServerBaseService"] = None,
        response: Optional[Response] = None,
        **data
    ):
        self._service = service

        self.filters = data.get("filters")
        self.order_by = data.get("order_by")
        self.page = self._resolve_int_metadata("page", "X-Page", response, data)
        self.page_size = self._resolve_int_metadata(
            "page_size", "X-Page-Size", response, data
        )
        self.total_pages = self._resolve_int_metadata(
            "total_pages", "X-Total-Pages", response, data
        )
        self.total_count = self._resolve_int_metadata(
            "total_count", "X-Total-Count", response, data
        )

        if "items" in data:
            self.items = data["items"]
        elif response is not None:
            self.items = [model(client=client, **entity) for entity in response.json()]
        else:
            self.items = []

    @staticmethod
    def _resolve_int_metadata(
        field_name: str,
        header_name: str,
        response: Optional[Response],
        data: dict,
    ) -> Optional[int]:
        field_value = data.get(field_name)
        if field_value is not None:
            return int(field_value)

        if response:
            header_value = response.headers.get(header_name)
            if header_value is not None:
                return int(header_value)

        return None

    @property
    def service(self) -> "HydroServerBaseService":
        return self._service

    def next_page(self):
        """Fetches the next page of data from HydroServer."""

        if not self._service:
            raise NotImplementedError("Pagination not enabled for this collection.")

        return self._service.list(
            **(self.filters or {}),
            page=(self.page or 0) + 1,
            page_size=self.page_size or 100,
            order_by=self.order_by or ...
        )

    def previous_page(self):
        """Fetches the previous page of data from HydroServer."""

        if not self._service:
            raise NotImplementedError("Pagination not enabled for this collection.")

        if not self.page or self.page <= 1:
            return None

        return self._service.list(
            **(self.filters or {}),
            page=self.page - 1,
            page_size=self.page_size or 100,
            order_by=self.order_by or ...
        )

    def fetch_all(self) -> "HydroServerCollection":
        """Fetches all pages of data from HydroServer for this collection."""

        if not self._service:
            raise NotImplementedError("Pagination not enabled for this collection.")

        all_items = []
        current_page = self.page or 1
        page_size = self.page_size or 100
        total_pages = self.total_pages

        page_num = 1
        while total_pages is None or page_num <= total_pages:
            if page_num == current_page:
                all_items.extend(self.items)
            else:
                page = self._service.list(
                    **(self.filters or {}),
                    page=page_num,
                    page_size=page_size,
                    order_by=self.order_by or ...
                )
                if not page.items:
                    break
                all_items.extend(page.items)

                if page.total_pages is not None:
                    total_pages = page.total_pages

            page_num += 1

        return self.__class__(
            model=type(self.items[0]) if self.items else None,
            client=self.items[0].client if self.items else None,
            service=self._service,
            items=all_items,
            filters=self.filters,
            order_by=self.order_by,
            page=1,
            page_size=len(all_items),
            total_pages=1,
            total_count=len(all_items)
        )
