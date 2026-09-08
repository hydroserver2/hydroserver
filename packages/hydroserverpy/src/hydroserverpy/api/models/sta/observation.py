import pandas as pd
from typing import Optional, Any, List, TYPE_CHECKING
from dataclasses import dataclass
from requests import Response
from pydantic.alias_generators import to_snake

if TYPE_CHECKING:
    from hydroserverpy.api.models import Datastream


@dataclass
class ObservationCollection:
    dataframe: pd.DataFrame
    filters: Optional[dict[str, Any]] = None
    order_by: Optional[List[str]] = None
    offset: Optional[int] = None
    limit: Optional[int] = None
    total_count: Optional[int] = None

    def __init__(
        self,
        datastream: "Datastream",
        response: Optional[Response] = None,
        **data
    ):
        self.filters = data.get("filters")
        raw_order_by = data.get("order_by")
        if isinstance(raw_order_by, str):
            self.order_by = [item for item in raw_order_by.split(",") if item]
        else:
            self.order_by = raw_order_by

        if "dataframe" in data:
            payload_meta = {}
            self.dataframe = data["dataframe"]
        elif response is not None:
            payload = response.json()
            payload_meta = payload.pop("meta", {})
            self.dataframe = pd.DataFrame({to_snake(k): v for k, v in payload.items()})
            if "phenomenon_time" in self.dataframe.columns:
                self.dataframe["phenomenon_time"] = pd.to_datetime(
                    self.dataframe["phenomenon_time"], utc=True, format="ISO8601"
                )
        else:
            payload_meta = {}
            self.dataframe = pd.DataFrame()

        self.offset = self._resolve_int_metadata("offset", payload_meta, data)
        self.limit = self._resolve_int_metadata("limit", payload_meta, data)
        self.total_count = self._resolve_int_metadata(
            "total_count", payload_meta, data, meta_key="totalCount"
        )
        self.datastream = datastream

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

    def next_page(self):
        """Fetches the next page of data from HydroServer."""

        limit = self.limit or 100000

        return self.datastream.get_observations(
            **(self.filters or {}),
            offset=(self.offset or 0) + limit,
            limit=limit,
            order_by=self.order_by or ...,
        )

    def previous_page(self):
        """Fetches the previous page of data from HydroServer."""

        if not self.offset:
            return None

        limit = self.limit or 100000

        return self.datastream.get_observations(
            **(self.filters or {}),
            offset=max(0, self.offset - limit),
            limit=limit,
            order_by=self.order_by or ...,
        )

    def fetch_all(self) -> "ObservationCollection":
        """Fetches all pages of data from HydroServer for this collection."""

        all_dataframes = [self.dataframe]
        limit = self.limit or 100000
        total_count = self.total_count
        next_offset = (self.offset or 0) + len(self.dataframe)

        while total_count is None or next_offset < total_count:
            observations = self.datastream.get_observations(
                **(self.filters or {}),
                offset=next_offset,
                limit=limit,
                order_by=self.order_by or ...,
            )
            if observations.dataframe.empty:
                break
            all_dataframes.append(observations.dataframe)

            if observations.total_count is not None:
                total_count = observations.total_count

            next_offset += len(observations.dataframe)

        if not all_dataframes:
            merged_dataframe = self.dataframe.iloc[0:0].copy()
        else:
            merged_dataframe = pd.concat(all_dataframes, ignore_index=True)

        return self.__class__(
            dataframe=merged_dataframe,
            datastream=self.datastream,
            filters=self.filters,
            order_by=self.order_by or ...,
            offset=0,
            limit=len(merged_dataframe),
            total_count=len(merged_dataframe) if total_count is None else total_count,
        )
