from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from pydantic import ValidationError

from .exceptions import ETLError

_EXTRACTOR_ALIAS_MAP: dict[str, str] = {
    "source_uri": "sourceUri",
    "placeholder_variables": "placeholderVariables",
    "run_time_value": "runTimeValue",
}

_TRANSFORMER_ALIAS_MAP: dict[str, str] = {
    "header_row": "headerRow",
    "data_start_row": "dataStartRow",
    "identifier_type": "identifierType",
    "custom_format": "customFormat",
    "timezone_mode": "timezoneMode",
    "run_time_value": "runTimeValue",
    "jmespath": "JMESPath",
    "target_identifier": "targetIdentifier",
    "source_identifier": "sourceIdentifier",
    "data_transformations": "dataTransformations",
    "lookup_table_id": "lookupTableId",
}

_MISSING_RUNTIME_VAR_RE = re.compile(
    r"Missing required runtime variables needed to render field "
    r"'([^']+)' with template '([^']+)': (.+)$"
)
_SOURCE_INDEX_OOR_RE = re.compile(r"Source index '([^']+)' is out of range")
_SOURCE_COL_NOT_FOUND_RE = re.compile(
    r"Source column '([^']+)' not found in extracted data\."
)


def _alias(component: str, field: str) -> str:
    if component == "extractor":
        return _EXTRACTOR_ALIAS_MAP.get(field, field)
    if component == "transformer":
        return _TRANSFORMER_ALIAS_MAP.get(field, field)
    return field


def _format_loc(component: str, loc: Iterable[Any]) -> str:
    loc_list = list(loc)

    if (
        component == "extractor"
        and loc_list
        and loc_list[0] in ("HTTPExtractor", "LocalExtractor", "FTPExtractor")
    ):
        loc_list = loc_list[1:]
    if (
        component == "transformer"
        and loc_list
        and loc_list[0] in ("JSONTransformer", "CSVTransformer")
    ):
        loc_list = loc_list[1:]

    parts: list[str] = []
    for item in loc_list:
        if isinstance(item, int):
            if not parts:
                parts.append(f"[{item}]")
            else:
                parts[-1] = f"{parts[-1]}[{item}]"
            continue
        if isinstance(item, str):
            parts.append(_alias(component, item))
            continue
        parts.append(str(item))

    if not parts:
        return component
    return ".".join([component] + parts)


def _jsonish(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        if value == "":
            return '""'
        return repr(value)
    return repr(value)


def _normalize_message_text(msg: str) -> str:
    if msg.startswith("Value error, "):
        return msg[len("Value error, "):]
    return msg


def _daylight_savings_message(
    component: Optional[str],
    raw: Optional[dict[str, Any]],
    msg: str,
) -> Optional[str]:
    if not isinstance(raw, dict):
        return None

    ts = raw.get("timestamp") if "timestamp" in raw else raw
    if not isinstance(ts, dict):
        return None

    tz_mode = ts.get("timezoneMode") or ts.get("timezone_mode")
    tz_value = ts.get("timezone")
    if str(tz_mode) != "daylightSavings":
        return None

    if tz_value is None or str(tz_value).strip() == "":
        return (
            "Timezone information is required when daylight savings mode is enabled. "
            "Select a valid timezone such as America/Denver and try again."
        )

    if "Invalid IANA timezone" in msg:
        return (
            "The configured timezone is not recognized. "
            "Use a valid IANA timezone such as America/Denver and run the job again."
        )

    return None


def user_facing_error_from_validation_error(
    component: str,
    exc: ValidationError,
    *,
    raw: Optional[dict[str, Any]] = None,
) -> str:
    errs = exc.errors(include_url=False)

    if not errs:
        return f"Invalid {component} configuration."

    first = errs[0]
    loc = first.get("loc") or ()
    msg = first.get("msg") or "Invalid value"
    inp = first.get("input", None)

    special = _daylight_savings_message(component, raw, str(msg))
    if special:
        return special

    normalized_msg = _normalize_message_text(str(msg))
    known_message = _user_facing_error_from_text(normalized_msg)
    if known_message:
        return known_message

    path = _format_loc(component, loc)
    return (
        f"Invalid {component} configuration at {path}: {msg} (got {_jsonish(inp)}). "
        f"Update the Data Connection {component} settings."
    )


def _user_facing_error_from_text(msg_str: str) -> Optional[str]:
    msg_str = _normalize_message_text(msg_str)

    missing_runtime = _MISSING_RUNTIME_VAR_RE.search(msg_str)
    if missing_runtime:
        field_name = missing_runtime.group(1)
        missing_names = [name.strip() for name in missing_runtime.group(3).split(",")]
        missing_name = missing_names[0]
        if field_name in {"source_uri", "filepath"}:
            return (
                f"The extractor URL includes a placeholder '{missing_name}', but no value was supplied. "
                "Provide the missing value in the task variables."
            )
        return (
            f"A required task variable named '{missing_name}' was not provided. "
            "Add a value for it in the task configuration and run the job again."
        )

    if msg_str.startswith("Received an invalid timestamp key for the CSV transformer:"):
        return (
            "The timestamp column is set incorrectly. Index mode expects a 1-based column number (1 for the first column). "
            "Update the timestamp setting to a valid column index."
        )

    if msg_str.startswith("Received an invalid data start row for the CSV transformer:"):
        return (
            "The CSV header or data start row is set incorrectly. "
            "Confirm which row contains the column names and which row contains the first data record."
        )

    if msg_str.startswith("Transformer received invalid payload. Column with name "):
        return (
            "The column mapped as the timestamp does not exist in the file. "
            "Confirm the source layout and update the mapping."
        )

    if (
        "The CSV transformer received an invalid CSV payload." in msg_str
        and "header row" in msg_str
    ):
        return (
            "A required column was not found in the file header. "
            "The source file may have changed or the header row may be set incorrectly. "
            "Confirm the file layout and update the column mappings if needed."
        )

    if "Received an invalid JMESPath expression for the JSON transformer:" in msg_str:
        return (
            "The JSON query used to extract timestamps or values is invalid or returned unexpected data. "
            "Review and correct the JMESPath expression."
        )

    if "did not match anything in the JSON payload" in msg_str:
        return (
            "Failed to find the timestamp or value using the current JSON query. "
            "Confirm the JMESPath expression matches the structure returned by the source."
        )

    if "The configured timestamp key '" in msg_str and "JSON records returned by the JMESPath expression" in msg_str:
        return (
            "The job could not find the expected timestamp or value fields using the current JSON query. "
            "Confirm the JMESPath expression matches the structure returned by the source."
        )

    if "The JSON transformer received a payload that is not valid JSON." in msg_str:
        return (
            "The source did not return valid JSON. "
            "Verify the URL points to a JSON endpoint."
        )

    if msg_str.startswith("Failed to connect to "):
        return (
            "Failed to connect to the source system. This may be temporary; try again shortly. "
            "If it persists, the source system may be offline."
        )

    if msg_str.startswith("The requested data could not be found at "):
        return (
            "The requested data could not be found on the source system. "
            "Verify the URL is correct and that the file or endpoint still exists."
        )

    if msg_str.startswith("Failed to authenticate with "):
        return (
            "Authentication with the source system failed. The username, password, or token may be incorrect or expired. "
            "Update the credentials and try again."
        )

    if msg_str.startswith("No data was returned from "):
        return (
            "No observations were returned from the source system. "
            "Confirm the configured source system has observations available for the requested time range."
        )

    if "could not find one or more destination datastreams" in msg_str.lower():
        return (
            "One or more destination datastream identifiers could not be found in HydroServer. "
            "Update the task mappings to use valid datastream IDs."
        )

    if "could not find a destination datastream" in msg_str.lower():
        return (
            "One or more destination datastream identifiers could not be found in HydroServer. "
            "Update the task mappings to use valid datastream IDs."
        )

    if (
        "destination datastream with id" in msg_str.lower()
        and "does not exist on this hydroserver instance" in msg_str.lower()
    ):
        return (
            "One or more destination datastream identifiers could not be found in HydroServer. "
            "Update the task mappings to use valid datastream IDs."
        )

    if "hydroserver rejected the load due to authorization" in msg_str.lower():
        return (
            "HydroServer rejected the load due to authorization. "
            "Confirm the target datastream(s) belong to this workspace and the job has permission to write."
        )

    if "hydroserver rejected some or all of the data" in msg_str.lower():
        return (
            "HydroServer rejected some or all of the data. "
            "Verify the transformed timestamps/values are valid and the target datastream mappings are correct."
        )

    source_index = _SOURCE_INDEX_OOR_RE.search(msg_str)
    if source_index:
        return (
            f"A mapping source index ({source_index.group(1)}) is out of range for the extracted data. "
            "Update task.mappings sourceIdentifier values (or switch identifierType) to match the extracted columns."
        )

    source_column = _SOURCE_COL_NOT_FOUND_RE.search(msg_str)
    if source_column:
        return (
            f"A mapped field named '{source_column.group(1)}' was not found in the extracted data. "
            "Update the task mapping so the source identifier matches the JSON."
        )

    if msg_str.startswith("Failed to compile arithmetic expression for data target:"):
        return msg_str

    if msg_str.startswith("Invalid timestamp UTC offset "):
        return (
            "The timestamp UTC offset is not valid. "
            "Use a value such as -0700 or -07:00 and try again."
        )

    if msg_str.startswith("Invalid timestamp configuration. Timestamp format is required"):
        return (
            "A custom timestamp format is required when the timestamp type is set to custom. "
            "Provide a valid format string and try again."
        )

    if msg_str.startswith("Invalid timestamp format string "):
        return (
            "The custom timestamp format is not valid. "
            "Use a valid strftime format such as %Y-%m-%d %H:%M:%S and try again."
        )

    if msg_str.startswith("Invalid timezone configuration. Default timezone value must not be provided"):
        return (
            "Timezone information should not be provided when the timestamps already include their own timezone values. "
            "Clear the timezone setting and run the job again."
        )

    return None


def user_facing_error_from_exception(exc: Exception) -> Optional[str]:
    msg_str = str(exc)

    special = _daylight_savings_message(None, None, msg_str)
    if special:
        return special

    if isinstance(exc, KeyError):
        name = exc.args[0] if exc.args else None
        if isinstance(name, str) and name:
            return (
                f"A required task variable named '{name}' was not provided. "
                "Add a value for it in the task configuration and run the job again."
            )

    return _user_facing_error_from_text(msg_str)


def coerce_known_etl_error(
    exc: Exception,
    *,
    component: Optional[str] = None,
    raw: Optional[dict[str, Any]] = None,
) -> Exception:
    if isinstance(exc, ValidationError):
        if component is None:
            return ETLError(str(exc))
        return ETLError(user_facing_error_from_validation_error(component, exc, raw=raw))

    message = user_facing_error_from_exception(exc)
    if message is not None:
        if isinstance(exc, ETLError) and message == str(exc):
            return exc
        return ETLError(message)

    return exc
