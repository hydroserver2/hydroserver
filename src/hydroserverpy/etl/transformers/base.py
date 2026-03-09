import logging
import pandas as pd
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Union, TextIO
from pydantic import BaseModel, Field
from ..models.base import ETLComponent
from ..models.timestamp import Timestamp
from ..utils import summarize_list
from ..operations import DataOperation
from ..exceptions import ETLError


logger = logging.getLogger(__name__)


class ETLTargetPath(BaseModel):
    target_identifier: Union[str, int]
    data_operations: list[DataOperation] = Field(default_factory=list)


class ETLDataMapping(BaseModel):
    source_identifier: Union[str, int]
    target_paths: list[ETLTargetPath]


class Transformer(ETLComponent, Timestamp, ABC):
    timestamp_key: str

    @abstractmethod
    def transform(
        self,
        payload: Union[str, TextIO, BytesIO],
        data_mappings: list[ETLDataMapping],
        **kwargs
    ) -> pd.DataFrame:
        """
        Parse the raw extracted payload into a long-format DataFrame with columns
        'timestamp', 'value', and 'target_id', then pass it to standardize_dataframe.

        Source column resolution, one-to-many fan-out, and reshaping from the raw
        payload format into long format are the responsibility of this method.
        Timestamp normalization, numeric coercion, deduplication, and data operations
        are applied by standardize_dataframe.
        """
        ...

    def standardize_dataframe(
        self,
        df: pd.DataFrame,
        data_mappings: list[ETLDataMapping],
    ) -> pd.DataFrame:
        """
        Normalize and apply data operations to a long-format DataFrame.

        Expects a DataFrame with columns 'timestamp', 'value', and 'target_id' as
        produced by transform(). For each target group, normalizes the timestamp
        column to UTC, coerces values to numeric, applies the configured data
        operations in order, and deduplicates on timestamp keeping the last occurrence.

        Returns a long-format DataFrame with the same three columns.
        """

        logger.debug(
            "Standardizing dataframe (rows=%s, targets=%s).",
            len(df),
            df["target_id"].nunique() if not df.empty else 0,
        )

        if df.empty:
            return pd.DataFrame(columns=["timestamp", "value", "target_id"])

        # Normalize timestamp column to UTC
        if "timestamp" not in df.columns:
            raise ETLError(
                f"Transformer received invalid payload. "
                f"Column with name '{self.timestamp_key}' not found in data. Provided columns: "
                f"{summarize_list(list(df.columns), max_items=30)}"
            )

        logger.debug(
            "Normalizing timestamps (timezoneType=%r, format=%r).",
            self.timezone_type, self.timestamp_format,
        )

        df = df.copy()
        df["timestamp"] = self.parse_series_to_utc(df["timestamp"])

        # Build target_id → ETLTargetPath lookup for operation dispatch
        target_path_map: dict[str, ETLTargetPath] = {
            str(target_path.target_identifier): target_path
            for data_mapping in data_mappings
            for target_path in data_mapping.target_paths
        }

        logger.debug(
            "Applying operations to %s target(s): %s",
            len(target_path_map),
            summarize_list(list(target_path_map.keys()), max_items=30),
        )

        result_frames = []

        for target_id, group in df.groupby("target_id", sort=False):
            target_df = group[["timestamp", "value"]].copy()
            path = target_path_map.get(str(target_id))
            if path is not None:
                target_df = self.apply_data_transformations(target_df, path)
            target_df = target_df.drop_duplicates(subset=["timestamp"], keep="last")
            target_df["target_id"] = str(target_id)
            result_frames.append(target_df)

        result = pd.concat(result_frames, ignore_index=True)

        logger.debug("Standardized dataframe shape: %s", result.shape)

        return result

    @staticmethod
    def reshape_dataframe_wide_to_long(
        df: pd.DataFrame,
        data_mappings: list["ETLDataMapping"],
    ) -> pd.DataFrame:
        """
        Reshape a wide-format DataFrame into long format suitable for standardize_dataframe.

        The input DataFrame must have a 'timestamp' column and one column per source
        identifier referenced by data_mappings. Each source column is fanned out to one
        row per target path that references it, producing a DataFrame with columns
        'timestamp', 'value', and 'target_id'.

        One-to-many mappings (a single source column mapped to multiple targets) produce
        one row per target per timestamp. If no mappings produce output, an empty
        long-format DataFrame with the correct columns is returned.
        """

        logger.debug(
            "Fanning out %s source mapping(s) into long format (%s total target path(s)).",
            len(data_mappings),
            sum(len(m.target_paths) for m in data_mappings),
        )

        long_frames = []

        for data_mapping in data_mappings:
            source_column = Transformer.resolve_source_column(df, data_mapping.source_identifier)
            for target_path in data_mapping.target_paths:
                target_df = df[["timestamp", source_column]].rename(
                    columns={source_column: "value"}
                ).copy()
                target_df["target_id"] = str(target_path.target_identifier)
                long_frames.append(target_df)

        if not long_frames:
            return pd.DataFrame(columns=["timestamp", "value", "target_id"])

        long_df = pd.concat(long_frames, ignore_index=True)

        logger.debug(
            "Long-format DataFrame assembled: %s rows, %s target(s).",
            len(long_df),
            long_df["target_id"].nunique(),
        )

        return long_df

    @staticmethod
    def resolve_source_column(df: pd.DataFrame, source_id: Union[str, int]) -> str:
        """
        Resolve a column identifier to a valid column name in a DataFrame.

        Accepts either an integer index or a column name, validates that it exists
        in the DataFrame, and returns the corresponding column name. Integer source
        IDs are treated as positional column indices unless the integer also exists
        as a column label, in which case the label takes precedence.
        """

        if isinstance(source_id, int) and source_id not in df.columns:
            try:
                return df.columns[source_id]
            except IndexError as e:
                raise ETLError(
                    f"Source index '{source_id}' is out of range ({len(df.columns)}) for extracted data. "
                    f"Extracted columns: {summarize_list(list(df.columns), max_items=30)}"
                ) from e

        if source_id not in df.columns:
            raise ETLError(
                f"Source column '{source_id}' not found in extracted data. "
                f"Extracted columns: {summarize_list(list(df.columns), max_items=30)}"
            )

        return source_id

    @staticmethod
    def apply_data_transformations(
        df: pd.DataFrame,
        path: ETLTargetPath,
    ) -> pd.DataFrame:
        """
        Apply the configured sequence of data operations for a target path to a
        two-column (timestamp, value) DataFrame.

        The value column is coerced to numeric before operations are applied, with
        non-numeric values converted to NaN. Each operation in the target path is
        applied in order, receiving and returning a (timestamp, value) DataFrame.
        Operations that only need the value column (e.g. arithmetic expressions,
        rating curves) may ignore the timestamp column. Operations that need temporal
        context (e.g. aggregation) may use both columns.

        The returned DataFrame preserves the (timestamp, value) structure.
        """

        result = df.copy()

        if pd.api.types.is_string_dtype(result["value"]):
            result["value"] = pd.to_numeric(result["value"], errors="coerce")

        for operation in path.data_operations:
            result = operation.apply(result)

        return result
