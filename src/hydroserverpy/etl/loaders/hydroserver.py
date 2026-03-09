import logging
import traceback
import pandas as pd
from typing import Union, Optional
from pydantic import ConfigDict
from datetime import datetime
from hydroserverpy import HydroServer
from .base import Loader, ETLLoaderResult, ETLTargetResult
from ..exceptions import ETLError


logger = logging.getLogger(__name__)


class HydroServerLoader(Loader):
    client: HydroServer
    chunk_size: int = 5000

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def load(
        self,
        payload: pd.DataFrame,
        **kwargs
    ) -> ETLLoaderResult:
        """
        Load observations from a long-format DataFrame to corresponding HydroServer
        datastreams.

        The payload is expected to have columns 'timestamp', 'value', and 'target_id'.
        Each unique target_id is resolved to a HydroServer datastream. Observations
        already present in HydroServer (at or before the datastream's phenomenon_end_time)
        are skipped per target. Remaining observations are uploaded in chunks.
        """

        target_ids = payload["target_id"].unique()

        logger.debug("Resolving %s destination datastream(s).", len(target_ids))

        datastreams = {}
        missing_datastreams = []

        for target_id in target_ids:
            try:
                datastreams[target_id] = self.client.datastreams.get(target_id)
            except Exception as e:
                if str(e).startswith("404"):
                    missing_datastreams.append(target_id)
                else:
                    raise ETLError(
                        f"The HydroServer data loader could not find a destination datastream "
                        f"with ID '{target_id}'. "
                        f"Ensure the HydroServer connection is configured correctly "
                        f"and is authorized to access the datastream."
                    ) from e

        if missing_datastreams:
            raise ETLError(
                f"The HydroServer data loader could not find one or more destination datastreams. "
                f"Ensure the HydroServer connection is configured correctly, "
                f"all destination datastreams exist on the configured HydroServer instance, "
                f"and the provided connection is authorized to access the datastreams. "
                f"Missing datastream IDs: {', '.join(sorted(str(i) for i in missing_datastreams))}."
            )

        etl_results = ETLLoaderResult()

        for target_id, datastream in datastreams.items():
            etl_results.target_results[target_id] = ETLTargetResult(
                target_identifier=target_id,
            )

            target_df = (
                payload[payload["target_id"] == target_id][["timestamp", "value"]]
                .dropna(subset=["value"])
                .copy()
            )

            if datastream.phenomenon_end_time is not None:
                target_df = target_df.loc[target_df["timestamp"] > datastream.phenomenon_end_time]

            if target_df.empty:
                etl_results.skipped_count += 1
                etl_results.target_results[target_id].status = "skipped"
                continue

            observations_to_load = len(target_df)

            logger.info(
                "Uploading %s observation(s) to datastream %s (%s chunk(s), chunk_size=%s).",
                observations_to_load,
                target_id,
                (observations_to_load + self.chunk_size - 1) // self.chunk_size,
                self.chunk_size,
            )

            for start_idx in range(0, observations_to_load, self.chunk_size):
                end_idx = min(start_idx + self.chunk_size, observations_to_load)
                chunk = target_df.iloc[start_idx:end_idx]

                try:
                    self.client.datastreams.load_observations(
                        uid=datastream.uid, observations=chunk
                    )
                    etl_results.target_results[target_id].values_loaded += len(chunk)
                except Exception as e:
                    etl_results.target_results[target_id].status = "failed"
                    etl_results.target_results[target_id].error = str(e)
                    etl_results.target_results[target_id].traceback = traceback.format_exc()
                    break

            if not etl_results.target_results[target_id].values_loaded > 0:
                etl_results.target_results[target_id].status = "skipped"

            if etl_results.target_results[target_id].status not in ["skipped", "failed"]:
                etl_results.target_results[target_id].status = "success"

        etl_results.aggregate_results()

        return etl_results

    def target_loaded_through(
        self,
        target_identifier: Union[str, int]
    ) -> Optional[datetime]:
        """
        Retrieve the timestamp through which data is loaded for a given HydroServer datastream.
        """

        try:
            datastream = self.client.datastreams.get(target_identifier)
        except Exception as e:
            if str(e).startswith("404"):
                raise ETLError(
                    f"The HydroServer data loader could not find a destination datastream "
                    f"with ID '{target_identifier}'. "
                    f"Ensure the HydroServer connection is configured correctly "
                    f"and is authorized to access the datastream."
                ) from e
            else:
                raise ETLError(
                    f"The HydroServer data loader failed to retrieve a destination datastream "
                    f"with ID '{target_identifier}'. "
                    f"Ensure the HydroServer connection is configured correctly "
                    f"and is authorized to access the datastream."
                ) from e

        return datastream.phenomenon_end_time
