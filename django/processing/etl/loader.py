import uuid
import logging
import traceback
import pandas as pd
from datetime import datetime, timezone
from typing import Union, Optional
from pydantic import ConfigDict

from core.sta.models import Datastream
from core.sta.services import ObservationService
from interfaces.api.schemas import ObservationBulkPostBody

from hydroserverpy.etl.loaders import Loader, ETLLoaderResult, ETLTargetResult
from hydroserverpy.etl.exceptions import ETLError


logger = logging.getLogger(__name__)
observation_service = ObservationService()


class HydroServerInternalLoader(Loader):
    chunk_size: int = 5000

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @staticmethod
    def _format_cutoff(value: Optional[datetime]) -> str:
        return value.isoformat() if value is not None else "None"

    def load(
        self,
        payload: pd.DataFrame,
        **kwargs
    ) -> ETLLoaderResult:
        """
        Load observations from a DataFrame to corresponding HydroServer datastreams.
        """

        target_ids = payload["target_id"].unique()

        logger.debug("Resolving %s destination datastream(s).", len(target_ids))

        datastreams = {}
        missing_datastreams = []
        task = kwargs["task_instance"]

        for target_id in target_ids:
            try:
                datastreams[target_id] = Datastream.objects.get(pk=uuid.UUID(target_id))
            except Datastream.DoesNotExist:
                missing_datastreams.append(target_id)
            except Exception as e:
                raise ETLError(
                    f"Encountered an unexpected error "
                    f"while loading destination datastream with ID: '{target_id}'. "
                    f"Ensure the datastream UUID is formatted correctly."
                ) from e

        if missing_datastreams:
            raise ETLError(
                f"One or more destination datastreams do not exist on this HydroServer instance. "
                f"Ensure the datastream IDs are correct. "
                f"Missing datastream IDs: {', '.join(sorted(missing_datastreams))}."
            )

        if not datastreams or any(datastream.phenomenon_end_time is None for datastream in datastreams.values()):
            earliest_phenomenon_end_time = None
        else:
            earliest_phenomenon_end_time = min(
                datastream.phenomenon_end_time for datastream in datastreams.values()
            )

        if earliest_phenomenon_end_time is not None:
            payload = payload[payload["timestamp"] > earliest_phenomenon_end_time]

        etl_results = ETLLoaderResult()

        for target_id, datastream in datastreams.items():
            etl_results.target_results[target_id] = ETLTargetResult(
                target_identifier=target_id,
            )

            datastream_df = (
                payload[payload["target_id"] == target_id][["timestamp", "value"]]
                .dropna(subset=["value"])
                .copy()
            )

            if datastream.phenomenon_end_time is not None:
                datastream_df = datastream_df.loc[datastream_df["timestamp"] > datastream.phenomenon_end_time]

            if datastream_df.empty:
                etl_results.skipped_count += 1
                etl_results.target_results[target_id].status = "skipped"
                logger.warning(
                    "No new observations for %s after filtering; skipping.",
                    target_id,
                )
                logger.info(
                    "Load result: loaded=0 available=0 cutoff=%s",
                    self._format_cutoff(datastream.phenomenon_end_time),
                )
                continue

            datastream_observations_to_load = len(datastream_df)

            logger.debug(
                "Uploading %s observation(s) to datastream %s (%s chunk(s), chunk_size=%s)",
                datastream_observations_to_load,
                target_id,
                (datastream_observations_to_load + self.chunk_size - 1) // self.chunk_size,
                self.chunk_size,
            )

            for start_idx in range(0, datastream_observations_to_load, self.chunk_size):
                end_idx = min(start_idx + self.chunk_size, datastream_observations_to_load)
                chunk = datastream_df.iloc[start_idx:end_idx]

                try:
                    observation_service.bulk_create(
                        principal=task.workspace.owner,
                        data=ObservationBulkPostBody(
                            fields=["phenomenonTime", "result"],
                            data=chunk.values.tolist(),
                        ),
                        datastream_id=datastream.pk,
                        mode="append",
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

            logger.info(
                "Load result: loaded=%s available=%s cutoff=%s",
                etl_results.target_results[target_id].values_loaded,
                datastream_observations_to_load,
                self._format_cutoff(datastream.phenomenon_end_time),
            )

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
            datastream = Datastream.objects.get(pk=uuid.UUID(target_identifier))
        except Datastream.DoesNotExist as e:
            raise ETLError(
                f"The destination datastream with ID '{target_identifier}' "
                f"does not exist on this HydroServer instance. "
                f"Ensure the datastream ID is correct."
            ) from e
        except Exception as e:
            raise ETLError(
                f"Encountered an unexpected error "
                f"while loading destination datastream with ID: '{target_identifier}'. "
                f"Ensure the datastream UUID is formatted correctly."
            ) from e

        return datastream.phenomenon_end_time or datetime(1970, 1, 1, tzinfo=timezone.utc)
