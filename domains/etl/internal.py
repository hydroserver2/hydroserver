import uuid
import logging
import traceback
import pandas as pd
from datetime import datetime
from io import BytesIO
from typing import Union, Optional, TextIO
from pydantic import ConfigDict
from django.db.models import Min
from domains.sta.models import Datastream, Observation
from domains.sta.services import ObservationService
from interfaces.api.schemas.observation import ObservationBulkPostBody
from hydroserverpy.etl import extractors, transformers
from hydroserverpy.etl.transformers import ETLDataMapping
from hydroserverpy.etl.loaders import Loader, ETLLoaderResult, ETLTargetResult
from hydroserverpy.etl.exceptions import ETLError


logger = logging.getLogger(__name__)
observation_service = ObservationService()


class HydroServerInternalExtractor(extractors.Extractor):
    def extract(
        self,
        **kwargs
    ) -> Union[str, TextIO, BytesIO]:
        """
        HydroServer's internal transformer will query data directly from the ORM to build a DataFrame.
        Since there's nothing to extract in this step, just return an empty string.
        """

        return ""


class HydroServerInternalTransformer(transformers.Transformer):
    def transform(
        self,
        payload: Union[str, TextIO, BytesIO],
        data_mappings: list[ETLDataMapping],
        **kwargs
    ) -> pd.DataFrame:
        """
        Load datastream observations from the ORM into a DataFrame.

        The payload is ignored; data is sourced directly from the Observation ORM.
        For each data mapping, the source datastream is queried once and the resulting
        DataFrame is fanned out to each target path. Per-target phenomenon_end_time
        filtering is applied in pandas after the query to avoid re-querying the ORM
        for one-to-many mappings.
        """

        result_dfs = []

        for data_mapping in data_mappings:
            source_datastream_id = uuid.UUID(str(data_mapping.source_identifier))

            earliest_end_time = Datastream.objects.filter(
                id__in=[target_path.target_identifier for target_path in data_mapping.target_paths]
            ).aggregate(
                earliest=Min("phenomenon_end_time")
            )["earliest"]

            queryset = Observation.objects.filter(datastream_id=source_datastream_id)
            if earliest_end_time is not None:
                queryset = queryset.filter(phenomenon_time__gt=earliest_end_time)

            source_df = pd.DataFrame(list(queryset.values("phenomenon_time", "result")))

            if source_df.empty:
                continue

            source_df = source_df.rename(
                columns={"phenomenon_time": "timestamp", "result": "value"}
            )

            for target_path in data_mapping.target_paths:
                target_id = str(target_path.target_identifier)

                phenomenon_end_time = (
                    Datastream.objects.filter(id=target_path.target_identifier)
                    .values_list("phenomenon_end_time", flat=True)
                    .first()
                )

                target_df = source_df.copy()

                if phenomenon_end_time is not None:
                    target_df = target_df[target_df["timestamp"] > phenomenon_end_time]

                if target_df.empty:
                    continue

                target_df = target_df.copy()
                target_df["target_id"] = target_id
                result_dfs.append(target_df)

        if not result_dfs:
            return pd.DataFrame(columns=["timestamp", "value", "target_id"])

        return self.standardize_dataframe(
            pd.concat(result_dfs, ignore_index=True),
            data_mappings,
        )


class HydroServerInternalLoader(Loader):
    chunk_size: int = 5000

    model_config = ConfigDict(arbitrary_types_allowed=True)

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

        earliest_phenomenon_end_time = min(
            (
                datastream.phenomenon_end_time for datastream in datastreams.values()
                if datastream.phenomenon_end_time is not None
            ), default=None,
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
                continue

            datastream_observations_to_load = len(datastream_df)

            logger.info(
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

        return datastream.phenomenon_end_time
