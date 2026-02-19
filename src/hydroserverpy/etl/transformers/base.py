from abc import ABC, abstractmethod
import ast
from io import BytesIO
from functools import lru_cache
import logging
import os
import re
from typing import Any, List, Union
from urllib.parse import unquote, urlparse

import numpy as np
import pandas as pd
import requests

from ..timestamp_parser import TimestampParser
from ..etl_configuration import MappingPath, TransformerConfig, SourceTargetMapping
from ..logging_utils import summarize_list

ALLOWED_AST = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.UAdd,
    ast.USub,
    ast.Name,
    ast.Load,
    ast.Constant,
)


def _canonicalize_expr(expr: str) -> str:
    # normalize whitespace for cache hits; parentheses remain intact
    return re.sub(r"\s+", "", expr)


@lru_cache(maxsize=256)
def _compile_arithmetic_expr_canon(expr_no_ws: str):
    tree = ast.parse(expr_no_ws, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_AST):
            raise ValueError(
                "Only +, -, *, / with 'x' and numeric literals are allowed."
            )
        if isinstance(node, ast.Name) and node.id != "x":
            raise ValueError("Only the variable 'x' is allowed.")
        if isinstance(node, ast.Constant):
            val = node.value
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError("Only numeric literals are allowed.")
    return compile(tree, "<expr>", "eval")


def _compile_arithmetic_expr(expr: str):
    return _compile_arithmetic_expr_canon(_canonicalize_expr(expr))


logger = logging.getLogger(__name__)


def _rating_curve_reference(transformation: Any) -> str:
    lookup_url = getattr(transformation, "rating_curve_url", None)
    lookup_ref = (lookup_url or "").strip()
    if not lookup_ref:
        raise ValueError("Rating curve transformation is missing ratingCurveUrl.")

    return lookup_ref


def _read_rating_curve_bytes(lookup_ref: str) -> bytes:
    parsed = urlparse(lookup_ref)
    scheme = parsed.scheme.lower()

    if scheme in {"http", "https"}:
        try:
            response = requests.get(lookup_ref, timeout=30)
        except requests.exceptions.Timeout as exc:
            raise ValueError(
                f"Timed out while retrieving rating curve from '{lookup_ref}'."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ValueError(
                f"Could not connect to rating curve URL '{lookup_ref}'."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ValueError(
                f"Failed to retrieve rating curve from '{lookup_ref}'."
            ) from exc

        if response.status_code == 404:
            raise ValueError(f"Rating curve file not found at '{lookup_ref}'.")
        if response.status_code in (401, 403):
            raise ValueError(
                f"Authentication failed while retrieving rating curve from '{lookup_ref}'."
            )
        if response.status_code >= 400:
            raise ValueError(
                f"Rating curve request to '{lookup_ref}' returned HTTP {response.status_code}."
            )

        payload = response.content or b""
        if not payload:
            raise ValueError(f"Rating curve at '{lookup_ref}' is empty.")
        return payload

    path = lookup_ref
    if scheme == "file":
        netloc = parsed.netloc or ""
        path = unquote(parsed.path or "")
        if netloc:
            path = f"//{netloc}{path}"

    if not os.path.exists(path):
        raise ValueError(f"Rating curve file not found at '{lookup_ref}'.")

    try:
        with open(path, "rb") as file_obj:
            payload = file_obj.read()
    except OSError as exc:
        raise ValueError(
            f"Unable to read rating curve file from '{lookup_ref}'."
        ) from exc

    if not payload:
        raise ValueError(f"Rating curve at '{lookup_ref}' is empty.")

    return payload


@lru_cache(maxsize=128)
def _load_rating_curve(lookup_ref: str) -> tuple[np.ndarray, np.ndarray]:
    payload = _read_rating_curve_bytes(lookup_ref)

    try:
        lookup_df = pd.read_csv(BytesIO(payload))
    except Exception as exc:
        raise ValueError(
            f"Rating curve at '{lookup_ref}' is not a valid CSV file."
        ) from exc

    if lookup_df.shape[1] < 2:
        raise ValueError(
            f"Rating curve at '{lookup_ref}' must contain at least two columns (input and output)."
        )

    standardized = lookup_df.iloc[:, :2].copy()
    standardized.columns = ["input_value", "output_value"]
    standardized["input_value"] = pd.to_numeric(
        standardized["input_value"], errors="coerce"
    )
    standardized["output_value"] = pd.to_numeric(
        standardized["output_value"], errors="coerce"
    )
    standardized = (
        standardized.dropna(subset=["input_value", "output_value"])
        .sort_values("input_value")
        .drop_duplicates(subset=["input_value"], keep="last")
    )

    if standardized.empty or len(standardized.index) < 2:
        raise ValueError(
            f"Rating curve at '{lookup_ref}' must include at least two numeric rows."
        )

    return (
        standardized["input_value"].to_numpy(dtype=np.float64),
        standardized["output_value"].to_numpy(dtype=np.float64),
    )


def _apply_rating_curve_transformation(
    series: pd.Series, path: MappingPath, transformation: Any
) -> pd.Series:
    lookup_ref = _rating_curve_reference(transformation)
    transformed = Transformer.apply_rating_curve(series, lookup_ref)
    logger.debug(
        "Applied rating curve transformation for target=%r using reference=%r.",
        path.target_identifier,
        lookup_ref,
    )
    return transformed


class Transformer(ABC):
    def __init__(self, transformer_config: TransformerConfig):
        self.cfg = transformer_config
        self.timestamp = transformer_config.timestamp
        self.timestamp_parser = TimestampParser(self.timestamp)

    @abstractmethod
    def transform(self, *args, **kwargs) -> None:
        pass

    @property
    def needs_datastreams(self) -> bool:
        return False

    @staticmethod
    def apply_rating_curve(
        values: Union[pd.Series, np.ndarray, List[float]], rating_curve_url: str
    ) -> pd.Series:
        """Apply a rating curve using linear interpolation with endpoint clamping."""

        source = (
            values
            if isinstance(values, pd.Series)
            else pd.Series(values, dtype="float64")
        )
        lookup_input, lookup_output = _load_rating_curve(rating_curve_url)

        source_numeric = pd.to_numeric(source, errors="coerce")
        source_values = source_numeric.to_numpy(dtype=np.float64)
        finite_mask = np.isfinite(source_values)

        transformed = np.full(source_values.shape, np.nan, dtype=np.float64)
        if finite_mask.any():
            transformed[finite_mask] = np.interp(
                source_values[finite_mask],
                lookup_input,
                lookup_output,
                left=lookup_output[0],
                right=lookup_output[-1],
            )

        return pd.Series(transformed, index=source.index, dtype="float64")

    def standardize_dataframe(
        self, df: pd.DataFrame, mappings: List[SourceTargetMapping]
    ):
        logger.debug(
            "Standardizing extracted dataframe (rows=%s, columns=%s).",
            len(df),
            len(df.columns),
        )
        logger.debug(
            "Extracted dataframe columns (sample): %s",
            summarize_list(list(df.columns), max_items=30),
        )
        if not df.empty:
            # Avoid dumping full rows; just log a compact preview.
            preview = df.iloc[0].to_dict()
            for k, v in list(preview.items()):
                if isinstance(v, str) and len(v) > 128:
                    preview[k] = v[:128] + "...(truncated)"
            logger.debug("Extracted dataframe first-row preview: %s", preview)

        # 1) Normalize timestamp column
        df.rename(columns={self.timestamp.key: "timestamp"}, inplace=True)
        if "timestamp" not in df.columns:
            msg = f"Timestamp column '{self.timestamp.key}' not found in data."
            logger.error(
                "%s Available columns=%s",
                msg,
                summarize_list(list(df.columns), max_items=30),
            )
            raise ValueError(msg)
        logger.debug(
            "Normalized timestamp column '%s' -> 'timestamp' (timezoneMode=%r, format=%r).",
            self.timestamp.key,
            getattr(self.timestamp, "timezone_mode", None),
            getattr(self.timestamp, "format", None),
        )

        df["timestamp"] = self.timestamp_parser.parse_series(df["timestamp"])
        df = df.drop_duplicates(subset=["timestamp"], keep="last")

        def _resolve_source_col(s_id: Union[str, int]) -> str:
            if isinstance(s_id, int) and s_id not in df.columns:
                try:
                    return df.columns[s_id]
                except IndexError:
                    logger.error(
                        "Source index %s is out of range. Extracted columns count=%s, columns(sample)=%s",
                        s_id,
                        len(df.columns),
                        summarize_list(list(df.columns), max_items=30),
                    )
                    raise ValueError(
                        f"Source index {s_id} is out of range for extracted data."
                    )
            if s_id not in df.columns:
                logger.error(
                    "Source column %r not found. Available columns=%s",
                    s_id,
                    summarize_list(list(df.columns), max_items=30),
                )
                raise ValueError(f"Source column '{s_id}' not found in extracted data.")
            return s_id

        def _apply_transformations(series: pd.Series, path: MappingPath) -> pd.Series:
            out = series  # accumulator for sequential transforms
            if out.dtype == "object":
                out = pd.to_numeric(out, errors="coerce")

            for transformation in path.data_transformations:
                if transformation.type == "expression":
                    code = _compile_arithmetic_expr(transformation.expression)
                    try:
                        out = eval(code, {"__builtins__": {}}, {"x": out})
                    except Exception as ee:
                        logger.exception(
                            "Data transformation failed for target=%r expression=%r",
                            path.target_identifier,
                            transformation.expression,
                        )
                        raise
                elif transformation.type == "rating_curve":
                    out = _apply_rating_curve_transformation(out, path, transformation)
                else:
                    msg = f"Unsupported transformation type: {transformation.type}"
                    logger.error(msg)
                    raise ValueError(msg)
            return out

        # source target mappings may be one to many. Therefore, create a new column for each target and apply transformations
        transformed_df = pd.DataFrame(index=df.index)
        logger.debug(
            "Applying %s source mapping(s): %s",
            len(mappings),
            summarize_list([m.source_identifier for m in mappings], max_items=30),
        )
        for m in mappings:
            src_col = _resolve_source_col(m.source_identifier)
            base = df[src_col]
            for path in m.paths:
                target_col = str(path.target_identifier)
                transformed_df[target_col] = _apply_transformations(base, path)

        # 6) Keep only timestamp + target columns
        df = pd.concat([df[["timestamp"]], pd.DataFrame(transformed_df)], axis=1)

        logger.debug("Standardized dataframe created: %s", df.shape)

        return df
