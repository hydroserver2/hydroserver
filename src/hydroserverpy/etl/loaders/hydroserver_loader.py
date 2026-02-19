from __future__ import annotations
from typing import TYPE_CHECKING

from .base import Loader
import logging
import pandas as pd
from ..etl_configuration import Task, SourceTargetMapping
from dataclasses import dataclass

if TYPE_CHECKING:
    from hydroserverpy.api.client import HydroServer


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadSummary:
    cutoff: str
    timestamps_total: int
    timestamps_after_cutoff: int
    observations_available: int
    observations_loaded: int
    datastreams_loaded: int


class HydroServerLoader(Loader):
    """
    A class that extends the HydroServer client with ETL-specific functionalities.
    """

    def __init__(self, client: HydroServer, task_id):
        self.client = client
        self._begin_cache: dict[str, pd.Timestamp] = {}
        self.task_id = task_id

    def load(self, data: pd.DataFrame, task: Task) -> LoadSummary:
        """
        Load observations from a DataFrame to the HydroServer.
        :param data: A Pandas DataFrame where each column corresponds to a datastream.
        """
        logger.info("Saving data to HydroServer...")
        begin_date = self.earliest_begin_date(task)
        new_data = data[data["timestamp"] > begin_date]

        cutoff_value = (
            begin_date.isoformat()
            if hasattr(begin_date, "isoformat")
            else str(begin_date)
        )
        timestamps_total = len(data)
        timestamps_after_cutoff = len(new_data)
        observations_available = 0
        observations_loaded = 0
        datastreams_loaded = 0

        for col in new_data.columns.difference(["timestamp"]):
            try:
                datastream = self.client.datastreams.get(uid=str(col))
            except Exception as e:
                status = getattr(e, "status_code", None) or getattr(
                    getattr(e, "response", None), "status_code", None
                )
                if status == 404:
                    raise ValueError("The target datastream could not be found.") from e
                raise ValueError("HydroServer rejected some or all of the data.") from e

            ds_cutoff = getattr(datastream, "phenomenon_end_time", None)

            base_df = (
                new_data[["timestamp", col]]
                .rename(columns={col: "value"})
                .dropna(subset=["value"])
            )
            if ds_cutoff:
                base_df = base_df.loc[base_df["timestamp"] > ds_cutoff]

            df = base_df
            available = len(df)
            observations_available += available
            if df.empty:
                continue

            df = df.rename(columns={"timestamp": "phenomenon_time", "value": "result"})

            loaded = 0
            # Chunked upload
            CHUNK_SIZE = 5000
            total = len(df)
            for start in range(0, total, CHUNK_SIZE):
                end = min(start + CHUNK_SIZE, total)
                chunk = df.iloc[start:end]
                logger.debug(
                    "Uploading %s rows (%s-%s) to datastream %s",
                    len(chunk),
                    start,
                    end - 1,
                    col,
                )
                try:
                    self.client.datastreams.load_observations(
                        uid=str(col), observations=chunk
                    )
                    loaded += len(chunk)
                except Exception as e:
                    status = getattr(e, "status_code", None) or getattr(
                        getattr(e, "response", None), "status_code", None
                    )
                    if status == 404:
                        raise ValueError(
                            "The target datastream could not be found."
                        ) from e
                    if status == 400:
                        raise ValueError(
                            "HydroServer rejected some or all of the data."
                        ) from e
                    if status == 409 or "409" in str(e) or "Conflict" in str(e):
                        logger.info(
                            "409 Conflict for datastream %s on rows %s-%s; skipping remainder for this stream.",
                            col,
                            start,
                            end - 1,
                        )
                    raise

            if loaded > 0:
                datastreams_loaded += 1
            observations_loaded += loaded

        return LoadSummary(
            cutoff=cutoff_value,
            timestamps_total=timestamps_total,
            timestamps_after_cutoff=timestamps_after_cutoff,
            observations_available=observations_available,
            observations_loaded=observations_loaded,
            datastreams_loaded=datastreams_loaded,
        )

    def _fetch_earliest_begin(
        self, mappings: list[SourceTargetMapping]
    ) -> pd.Timestamp:
        logger.info(
            "Checking HydroServer for the most recent data already stored (so we only load new observations)..."
        )
        timestamps = []
        for m in mappings:
            for p in m["paths"] if isinstance(m, dict) else m.paths:
                datastream_id = (
                    p["targetIdentifier"]
                    if isinstance(p, dict)
                    else p.target_identifier
                )
                datastream = self.client.datastreams.get(datastream_id)
                raw = datastream.phenomenon_end_time or "1880-01-01"
                ts = pd.to_datetime(raw, utc=True)
                timestamps.append(ts)
        earliest = (
            min(timestamps) if timestamps else pd.Timestamp("1880-01-01", tz="UTC")
        )
        logger.debug("Found earliest begin date: %s", earliest)
        return earliest

    def earliest_begin_date(self, task: Task) -> pd.Timestamp:
        """
        Return earliest begin date for a task, or compute+cache it on first call.
        """
        key = task.name
        if key not in self._begin_cache:
            self._begin_cache[key] = self._fetch_earliest_begin(task.mappings)
        return self._begin_cache[key]
