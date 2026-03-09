import logging
import json
import jmespath
import pandas as pd
from io import BytesIO, TextIOBase, BufferedIOBase
from typing import Union, TextIO
from pydantic import model_validator
from jmespath.exceptions import JMESPathError
from .base import Transformer, ETLDataMapping
from ..exceptions import ETLError


logger = logging.getLogger(__name__)


class JSONTransformer(Transformer):
    jmespath: str

    @model_validator(mode="after")
    def validate_jmespath(self) -> "JSONTransformer":
        """
        Ensure that the jmespath expression is syntactically correct.
        """

        try:
            jmespath.compile(self.jmespath)
        except JMESPathError as e:
            raise ValueError(
                f"Received an invalid JMESPath expression for the JSON transformer: "
                f"{self.jmespath!r}. "
                f"Error: {str(e)}"
            ) from e

        return self

    def transform(
        self,
        payload: Union[str, TextIO, BytesIO],
        data_mappings: list[ETLDataMapping],
        **kwargs
    ) -> pd.DataFrame:
        """
        Parse a JSON payload into a long-format DataFrame with columns
        'timestamp', 'value', and 'target_id'.

        Applies the configured JMESPath expression to extract a list of records,
        builds a DataFrame from those records, fans out one-to-many mappings,
        and reshapes into long format before passing to standardize_dataframe
        for timestamp normalization, numeric coercion, data operations, and
        deduplication.

        The JMESPath expression is expected to return either a list of dicts
        or a single dict (which is wrapped in a list). The timestamp field
        must be present in each record under the configured timestamp_key.
        """

        if not isinstance(payload, (str, bytes, TextIOBase, BufferedIOBase)):
            raise ETLError(
                f"The JSON transformer received a payload object of type {type(payload).__name__}; "
                "expected one of: str, bytes, TextIO, BytesIO. "
                "Ensure the source system is returning a file-like object."
            )

        try:
            if isinstance(payload, (str, bytes)):
                json_data = json.loads(payload)
            else:
                json_data = json.load(payload)
        except json.JSONDecodeError as e:
            raise ETLError(
                "The JSON transformer received a payload that is not valid JSON. "
                "Ensure the source system is returning properly formatted JSON data."
            ) from e
        except Exception as e:
            raise ETLError(
                "The JSON transformer encountered an unexpected error while parsing the provided payload. "
                "Ensure the source system is returning properly formatted JSON data."
            ) from e

        if not isinstance(json_data, (dict, list)):
            raise ETLError(
                "The JSON transformer received a JSON payload that it cannot evaluate. "
                "The JSON payload must be a dictionary or a list at the top level."
            )

        logger.debug("Loaded JSON payload (type=%s).", type(json_data).__name__)

        try:
            data_points = jmespath.search(self.jmespath, json_data)
        except JMESPathError as e:
            raise ETLError(
                f"The JMESPath expression '{self.jmespath}' provided to the JSON transformer "
                f"could not be evaluated against the JSON payload. "
                f"Verify the expression and the payload structure are correct."
            ) from e

        if data_points is None:
            raise ETLError(
                f"The JMESPath expression '{self.jmespath}' provided to the JSON transformer "
                f"did not match anything in the JSON payload. "
                f"Verify the expression matches the structure of the source data."
            )

        if isinstance(data_points, dict):
            data_points = [data_points]

        logger.debug("Extracted %s JSON data point(s).", len(data_points))

        # Treat an empty result list as no data rather than a configuration error.
        if len(data_points) == 0:
            logger.debug("JMESPath returned empty list; returning empty long-format DataFrame.")
            return pd.DataFrame(columns=["timestamp", "value", "target_id"])

        df = pd.DataFrame(data_points)

        logger.debug("Built DataFrame from JSON records: %s rows, %s columns.", *df.shape)

        # Rename timestamp column and reshape wide → long format.
        # Each source column fans out to one row per target path that references it.
        if self.timestamp_key not in df.columns:
            raise ETLError(
                f"The configured timestamp key '{self.timestamp_key}' was not found in the "
                f"JSON records returned by the JMESPath expression. "
                f"Verify the timestamp key matches the field name in the source data."
            )

        df = df.rename(columns={self.timestamp_key: "timestamp"})
        df = self.reshape_dataframe_wide_to_long(
            df=df,
            data_mappings=data_mappings,
        )

        return self.standardize_dataframe(df, data_mappings)
