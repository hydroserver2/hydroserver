import logging
from io import BytesIO, StringIO, TextIOBase, BufferedIOBase
from typing import Literal, Union, TextIO, Optional
from pydantic import Field, model_validator
from pandas import DataFrame, read_csv
from pandas.errors import EmptyDataError
from .base import Transformer, ETLDataMapping
from ..exceptions import ETLError


logger = logging.getLogger(__name__)

CSVIdentifierType = Literal["name", "index"]
CSVDelimiterType = Literal[",", "|", "\t", ";", " "]


class CSVTransformer(Transformer):
    header_row: Optional[int] = Field(None, gt=0)
    data_start_row: int = Field(1, gt=0)
    delimiter: CSVDelimiterType = ","
    identifier_type: CSVIdentifierType = "name"

    @model_validator(mode="after")
    def validate_timestamp_key(self) -> "CSVTransformer":
        """
        Ensure the timestamp_key is valid for the configured identifier type.
        """

        if self.identifier_type == "index":
            try:
                value = int(self.timestamp_key)
            except (TypeError, ValueError):
                raise ValueError(
                    f"Received an invalid timestamp key for the CSV transformer: "
                    f"{self.timestamp_key} "
                    f"The timestamp key must be an integer "
                    f"when using index-based CSV column identifiers."
                )
            if value <= 0:
                raise ValueError(
                    f"Received an invalid timestamp key for the CSV transformer: "
                    f"{self.timestamp_key} "
                    f"The timestamp key must be greater than 0 "
                    f"when using index-based CSV column identifiers."
                )

        return self

    @model_validator(mode="after")
    def validate_data_start_row(self) -> "CSVTransformer":
        """
        Ensure data_start_row is greater than header_row when both are configured.
        """

        if self.header_row is not None and self.data_start_row <= self.header_row:
            raise ValueError(
                f"Received an invalid data start row for the CSV transformer: "
                f"The data start row must be greater than the header row if present."
                f"Received: header row: {self.header_row}; data start row: {self.data_start_row} "
            )
        return self

    def transform(
        self,
        payload: Union[str, TextIO, BytesIO],
        data_mappings: list[ETLDataMapping],
        **kwargs
    ) -> DataFrame:
        """
        Parse a CSV payload into a long-format DataFrame with columns
        'timestamp', 'value', and 'target_id'.

        Reads only the columns referenced by data_mappings, resolves source
        identifiers, fans out one-to-many mappings, and reshapes into long
        format before passing to standardize_dataframe for timestamp
        normalization, numeric coercion, data operations, and deduplication.
        """

        if not isinstance(payload, (str, bytes, TextIOBase, BufferedIOBase)):
            raise ETLError(
                f"The CSV transformer received a payload object of type {type(payload).__name__}; "
                "expected one of: str, bytes, TextIO, BytesIO. "
                "Ensure the extractor URI resolves to a file-like object."
            )

        use_index = self.identifier_type == "index"
        clean_payload = self.strip_comments(payload)

        if use_index:
            timestamp_position = int(self.timestamp_key) - 1

            try:
                source_positions = [
                    int(mapping.source_identifier) - 1
                    for mapping in data_mappings
                ]
            except Exception as e:
                raise ETLError(
                    f"Received one or more invalid source identifier keys for the CSV transformer. "
                    f"The source identifier keys must be integers "
                    f"when using index-based CSV column identifiers."
                ) from e

            if any(position < 0 for position in source_positions):
                raise ETLError(
                    f"Received one or more invalid source identifier keys for the CSV transformer. "
                    f"The source identifier keys must be greater than 0 "
                    f"when using index-based CSV column identifiers."
                )

            columns = [timestamp_position] + source_positions
            dtype = "string"

        else:
            columns = [self.timestamp_key] + [
                mapping.source_identifier for mapping in data_mappings
            ]
            dtype = {self.timestamp_key: "string"}

        logger.info("Reading CSV data.")
        logger.debug(
            "Parsing CSV (identifierType=%r, delimiter=%r, headerRow=%r, dataStartRow=%r, usecols=%r).",
            self.identifier_type, self.delimiter, self.header_row, self.data_start_row, columns,
        )

        try:
            header_idx = (self.header_row - 1) if self.header_row is not None else -1
            data_start_idx = self.data_start_row - 1
            df = read_csv(
                clean_payload,
                sep=self.delimiter,
                header=0 if not use_index else None,
                skiprows=[i for i in range(data_start_idx) if i != header_idx],
                usecols=columns,
                dtype=dtype,
            )
        except EmptyDataError as e:
            raise ETLError(
                "The CSV transformer received an empty CSV file. "
                "Ensure the provided source file contains valid CSV data."
            ) from e
        except Exception as e:
            exc_message = str(e)
            if "No columns to parse from file" in exc_message:
                raise ETLError(
                    "The CSV transformer received an empty CSV file. "
                    "Ensure the provided source file contains valid CSV data."
                ) from e
            elif "Usecols do not match columns" in exc_message or "not in list" in exc_message:
                raise ETLError(
                    "The CSV transformer received an invalid CSV payload. "
                    "One or more configured CSV columns were not found in the header row."
                ) from e
            else:
                raise ETLError(
                    "The CSV transformer encountered an unexpected error while parsing the CSV payload. "
                    "Ensure the source system is returning a valid CSV payload that matches "
                    "the settings configured for this transformer."
                ) from e

        logger.debug("CSV parsed: %s rows, %s columns.", *df.shape)

        # In index mode, relabel columns to 1-based string labels so that
        # source identifiers from task config (stored as strings) match correctly.
        if use_index:
            df.columns = [
                str(col + 1) if isinstance(col, int) else str(col)
                for col in columns
            ]

        # Rename timestamp column and reshape wide → long format.
        # Each source column fans out to one row per target path that references it.
        df = df.rename(columns={self.timestamp_key: "timestamp"})
        df = self.reshape_dataframe_wide_to_long(
            df=df,
            data_mappings=data_mappings,
        )

        return self.standardize_dataframe(df, data_mappings)

    @staticmethod
    def strip_comments(payload: Union[str, TextIO, BytesIO]) -> StringIO:
        """
        Remove lines whose first non-blank character is '#'.

        Reading the payload as text ensures that the original file contents are exactly preserved.
        Pandas’ heuristics can strip offsets and silently coerce failures to strings, so this
        method guarantees the raw text is parsed. Timestamps will be parsed during
        DataFrame standardization.
        """

        if isinstance(payload, str):
            lines = payload.splitlines(keepends=True)
        elif isinstance(payload, bytes):
            lines = payload.decode("utf-8", "ignore").splitlines(keepends=True)
        else:
            lines = (line.decode("utf-8", "ignore") if isinstance(line, bytes) else line
                     for line in payload)

        clean_lines = (line for line in lines if not line.lstrip().startswith("#"))

        return StringIO("".join(clean_lines))
