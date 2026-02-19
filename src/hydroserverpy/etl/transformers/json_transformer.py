import logging
import pandas as pd
from typing import Optional, Any, List
from .base import Transformer
import json
import jmespath
from ..etl_configuration import TransformerConfig, SourceTargetMapping


logger = logging.getLogger(__name__)


class JSONTransformer(Transformer):
    def __init__(self, transformer_config: TransformerConfig):
        super().__init__(transformer_config)
        self.jmespath = transformer_config.jmespath

    def transform(self, data_file, mappings: List[SourceTargetMapping]):
        """
        Transforms a JSON file-like object into the standard Pandas dataframe format.
        Since JMESPath can natively rename column names, the assumption is the timestamp column
        is always named 'timestamp' for JSON data or converted to 'timestamp' in the JMESPath query.

        Parameters:
            data_file: File-like object containing JSON data.

        Returns:
            pd.DataFrame: pandas DataFrames in the format pd.Timestamp, datastream_id_1, datastream_id_2, ...
        """
        if data_file is None:
            raise TypeError(
                "JSONTransformer received None; expected file-like, bytes, or str"
            )

        json_data = json.load(data_file)
        logger.debug("Loaded JSON payload (type=%s).", type(json_data).__name__)
        if not isinstance(json_data, (dict, list)):
            raise ValueError("The payload's expected fields were not found.")

        data_points = self.extract_data_points(json_data)
        if data_points is None:
            # JMESPath returned null: this usually means the expected field/path was not present.
            raise ValueError(
                "The timestamp or value key could not be found with the specified query."
            )
        if len(data_points) == 0:
            # Treat an empty result list as "no data" (not a configuration error).
            # Build an empty frame with the expected columns so standardization can proceed cleanly.
            cols = [self.timestamp.key] + [m.source_identifier for m in mappings]
            df = pd.DataFrame(columns=cols)
            return self.standardize_dataframe(df, mappings)

        logger.debug("Extracted %s JSON data point(s).", len(data_points))
        df = pd.DataFrame(data_points)

        return self.standardize_dataframe(df, mappings)

    def extract_data_points(self, json_data: Any) -> Optional[List[dict]]:
        """Extracts data points from the JSON data using the data_path."""
        data_points = jmespath.search(self.jmespath, json_data)
        if data_points is None:
            return None

        if isinstance(data_points, dict):
            data_points = [data_points]
        if isinstance(data_points, list):
            return data_points
        # Unexpected output type; surface it as a configuration issue.
        return None
