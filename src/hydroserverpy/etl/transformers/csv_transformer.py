from io import StringIO
import logging
import pandas as pd
from typing import Iterable, List, Union
from .base import Transformer
from ..etl_configuration import TransformerConfig, SourceTargetMapping


logger = logging.getLogger(__name__)


class CSVTransformer(Transformer):
    def __init__(self, transformer_config: TransformerConfig):
        super().__init__(transformer_config)

        # Pandas is zero-based while CSV is one-based so convert
        self.header_row = (
            None if self.cfg.header_row is None else self.cfg.header_row - 1
        )
        self.data_start_row = (
            self.cfg.data_start_row - 1 if self.cfg.data_start_row else 0
        )
        self.delimiter = self.cfg.delimiter or ","
        self.identifier_type = self.cfg.identifier_type or "name"

    def transform(
        self, data_file, mappings: List[SourceTargetMapping]
    ) -> Union[pd.DataFrame, None]:
        """
        Transforms a CSV file-like object into a Pandas DataFrame where the column
        names are replaced with their target datastream ids.

        Parameters:
            data_file: File-like object containing CSV data.
        Returns:
            observations_map (dict): Dict mapping datastream IDs to pandas DataFrames.
        """
        if data_file is None:
            raise TypeError(
                "CSVTransformer received None; expected file-like, bytes, or str"
            )

        clean_file = self._strip_comments(data_file)
        use_index = self.identifier_type == "index"

        if use_index:
            # Users will always interact in 1-based, so if the key is a column index, convert to 0-based to work with Pandas
            try:
                timestamp_pos = int(self.timestamp.key) - 1
            except Exception as e:
                raise ValueError(
                    "CSV transformer identifierType='index' requires timestamp.key to be a 1-based "
                    "column index string (example: '1')."
                ) from e
            try:
                source_positions = [int(m.source_identifier) - 1 for m in mappings]
            except Exception as e:
                raise ValueError(
                    "CSV transformer identifierType='index' requires each mapping sourceIdentifier to be a "
                    "1-based column index string (example: '2')."
                ) from e

            usecols = [timestamp_pos] + source_positions
            # When selecting columns by integer position, `dtype={col_name: ...}` can break because there is
            # no stable column name at parse time. Reading everything as string is safe; we coerce later.
            dtype = "string"
        else:
            usecols = [self.timestamp.key] + [m.source_identifier for m in mappings]
            dtype = {self.timestamp.key: "string"}

        logger.info("Reading CSV data...")
        logger.debug(
            "Parsing CSV (identifierType=%r, delimiter=%r, headerRow=%r, dataStartRow=%r, usecols=%r).",
            self.identifier_type,
            self.delimiter,
            getattr(self.cfg, "header_row", None),
            getattr(self.cfg, "data_start_row", None),
            usecols,
        )

        try:
            # Pandas’ heuristics strip offsets and silently coerce failures to strings.
            # Reading as pure text guarantees we always start with exactly what was in the file.
            # Timestamps will be parsed at df standardization time.
            df = pd.read_csv(
                clean_file,
                sep=self.delimiter,
                header=0,
                skiprows=self._build_skiprows(),
                usecols=usecols,
                dtype=dtype,
            )
            logger.debug("CSV file read into dataframe: %s", df.shape)
        except Exception as e:
            # Try to extract a safe preview of the header for "usecols do not match columns" failures.
            header_preview = None
            try:
                pos = clean_file.tell()
                clean_file.seek(0)
                header_preview = (clean_file.readline() or "").strip()
                clean_file.seek(pos)
            except Exception:
                header_preview = None

            msg = str(e)
            user_message = "One or more data rows contained unexpected values and could not be processed."
            if "No columns to parse from file" in msg:
                user_message = "The source system returned no data."
            elif "Usecols do not match columns" in msg or "not in list" in msg:
                user_message = "One or more configured CSV columns were not found in the header row."

            logger.error("Error reading CSV data: %s", user_message)
            raise ValueError(user_message) from e

        # In index mode, relabel columns back to original 1-based indices so base transformer can use integer labels directly
        if use_index:
            # Task config stores keys as strings; keep columns as strings so timestamp.key/sourceIdentifier match.
            df.columns = [str(c + 1) if isinstance(c, int) else str(c) for c in usecols]

        return self.standardize_dataframe(df, mappings)

    def _strip_comments(self, stream: Iterable[Union[str, bytes]]) -> StringIO:
        """
        Remove lines whose first non-blank char is '#'.
        Works for both text and binary iterables.
        """
        clean: list[str] = []

        for raw in stream:
            # normalize to bytes
            b = raw if isinstance(raw, bytes) else raw.encode("utf-8", "ignore")
            if b.lstrip().startswith(b"#"):
                continue
            clean.append(
                raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else raw
            )

        return StringIO("".join(clean))

    def _build_skiprows(self):
        return lambda idx: idx != self.header_row and idx < self.data_start_row
