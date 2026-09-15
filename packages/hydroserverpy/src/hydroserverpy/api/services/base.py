import json
import uuid
from typing import TYPE_CHECKING, Type, List, Union
from datetime import datetime
from hydroserverpy.api.models.base import HydroServerBaseModel, HydroServerCollection
from hydroserverpy.api.utils import sortby_to_camel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class HydroServerBaseService:
    model: Type[HydroServerBaseModel]

    def __init__(self, client: "HydroServer") -> None:
        self.client = client

    def list(
        self,
        offset: int = ...,
        limit: int = ...,
        sortby: List[str] = ...,
        fetch_all: bool = False,
        **kwargs
    ):
        kwargs = {
            k: v for k, v in kwargs.items() if v is not ...
        }
        params = kwargs.copy()
        params.update({
            "offset": offset,
            "limit": limit,
            "sortby": [sortby_to_camel(order) for order in sortby] if sortby is not ... else sortby
        })
        params = {
            k: ("null" if v is None else v)
            for k, v in params.items()
            if v is not ...
        }

        path = f"/{self.client.base_route}/{self.model.get_route()}"
        response = self.client.request("get", path, params=params)
        collection = HydroServerCollection(
            model=self.model,
            client=self.client,
            service=self,
            response=response,
            sortby=params.get("sortby"),
            filters={
                (k[:-3] if k.endswith("_id") else k): v
                for k, v in kwargs.items()
            }
        )
        if fetch_all is True:
            collection = collection.fetch_all()

        return collection

    def get(
        self,
        uid: Union[uuid.UUID, str]
    ):
        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}"
        payload = self.client.request("get", path).json()
        data = payload.get("data", payload)

        return self.model(
            client=self.client, uid=uuid.UUID(str(data.pop("id"))), **data
        )

    def create(self, **kwargs):
        path = f"/{self.client.base_route}/{self.model.get_route()}"
        headers = {"Content-type": "application/json"}
        response = self.client.request(
            "post", path, headers=headers, data=json.dumps(kwargs, default=self.default_serializer)
        ).json()

        return self.get(response["id"])

    def update(
        self,
        uid: Union[uuid.UUID, str],
        **kwargs
    ):
        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}"
        headers = {"Content-type": "application/json"}
        body = self.prune_unset(kwargs) or {}
        self.client.request(
            "patch", path, headers=headers, data=json.dumps(body, default=self.default_serializer)
        )

        return self.get(uid)

    def delete(
        self,
        uid: Union[uuid.UUID, str]
    ) -> None:
        path = f"/{self.client.base_route}/{self.model.get_route()}/{str(uid)}"
        self.client.request("delete", path)

    @staticmethod
    def default_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    def prune_unset(self, obj):
        if isinstance(obj, dict):
            return {
                k: self.prune_unset(v)
                for k, v in obj.items()
                if v is not ...
            }
        return obj
