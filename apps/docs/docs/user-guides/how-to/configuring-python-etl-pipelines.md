# Configuring Python ETL Pipelines

The `hydroserverpy.etl` package provides a framework for building Extract, Transform, and Load (ETL) pipelines that move time series data from external sources into a HydroServer instance. This guide covers how to configure a pipeline, run it, interpret results, and debug errors.

## Overview

A pipeline is made up of three components:

- An **Extractor** that retrieves raw data from a source (HTTP, FTP, or local file).
- A **Transformer** that parses the raw data into a standardized Pandas DataFrame.
- A **Loader** that writes the transformed observations to HydroServer datastreams.

These are assembled into an `ETLPipeline` and executed with a set of data mappings that describe which source columns map to which HydroServer datastream targets.

### Local pipelines vs. scheduled ETL tasks

HydroServer's scheduled ETL — the data connections and ETL tasks you create in the web app or with [`hs_api.dataconnections` and `hs_api.etltasks`](/user-guides/how-to/using-the-python-client#etl) — runs on this same engine on the server. Use a scheduled ETL task when HydroServer should fetch the data on a schedule. Build a pipeline yourself, as described on this page, when the data is only reachable from your own machine (for example a local file), when you need custom logic around the run, or when you want to test a configuration before scheduling it.

## Configuring a Pipeline

### Extractors

Extractors retrieve data from a source and return a file-like object. The `source_uri` field (`filepath` for FTP) supports template variables in `{braces}`, which are resolved at runtime using keyword arguments passed to `run()`.

**HTTP:**
```python
from hydroserverpy.etl.extractors import HTTPExtractor

extractor = HTTPExtractor(
    source_uri="https://api.example.com/data/{station_id}/export.csv"
)
```

If the source requires an API key or token, pass it as a request header with `auth_header_name` and `auth_header_value`:

```python
extractor = HTTPExtractor(
    source_uri="https://api.example.com/data/{station_id}/export.csv",
    auth_header_name="Authorization",
    auth_header_value="Bearer <token>",
)
```

**FTP:**
```python
from hydroserverpy.etl.extractors import FTPExtractor

extractor = FTPExtractor(
    host="ftp.example.com",
    filepath="/data/{station_id}/readings.csv",
    username="user",
    password="pass",
    port=21,
)
```

**Local file:**
```python
from hydroserverpy.etl.extractors import LocalFileExtractor

extractor = LocalFileExtractor(
    source_uri="/mnt/data/{station_id}/readings.csv"
)
```

### Transformers

Transformers parse the extracted payload into observations for each mapped target datastream.

**CSV:**
```python
from hydroserverpy.etl.transformers import CSVTransformer

transformer = CSVTransformer(
    timestamp_key="datetime",
    delimiter=",",
    header_row=1,
    data_start_row=2,
)
```

Use `identifier_type="index"` to reference columns by 1-based position instead of name:
```python
from hydroserverpy.etl.transformers import CSVTransformer

transformer = CSVTransformer(
    timestamp_key="1",
    identifier_type="index",
    data_start_row=3,
)
```

**JSON:**
```python
from hydroserverpy.etl.transformers import JSONTransformer

transformer = JSONTransformer(
    timestamp_key="timestamp",
    jmespath="response.data",
)
```

The `jmespath` expression selects the array of records from the JSON payload. Each selected record must contain a field named `timestamp_key`, and the [data mappings](#data-mappings) refer to the other fields by name. If the source uses different names, rename them in the expression, for example `data[].{timestamp: time, discharge: q}`. The JSON transformer has no `identifier_type` option; fields are always referenced by name.

### Timestamp Configuration

Every transformer requires a `timestamp_key` identifying the source column that contains timestamps, and a set of timestamp configuration fields that control how those values are parsed and normalized to UTC.

#### Timestamp type

| `timestamp_type` | Behaviour |
|---|---|
| `"iso"` (default) | Parses timestamps using pandas ISO 8601 inference. Handles most standard formats automatically. |
| `"custom"` | Parses timestamps using a `strftime`-compatible format string provided via `timestamp_format`. Required when the source timestamps are not in a standard ISO 8601 format. |

```python
from hydroserverpy.etl.transformers import CSVTransformer

# Custom format example — timestamps like "01/15/2024 08:30:00"
transformer = CSVTransformer(
    timestamp_key="datetime",
    timestamp_type="custom",
    timestamp_format="%m/%d/%Y %H:%M:%S",
    timezone_type="utc",
)
```

#### Timezone type

| `timezone_type` | Behaviour | Requires |
|---|---|---|
| `None` (default) | Reads timezone offset from the timestamp string itself. Falls back to UTC if the timestamps are naive. | — |
| `"utc"` | Treats all timestamps as UTC. | — |
| `"offset"` | Treats timestamps as naive and applies a fixed UTC offset. Strips any embedded offset if present. | `timezone` in `±HHMM` or `±HH:MM` format |
| `"iana"` | Treats timestamps as naive and applies a named IANA timezone. Strips any embedded offset if present. | `timezone` as a valid IANA name |

```python
from hydroserverpy.etl.transformers import CSVTransformer

# Fixed UTC offset — timestamps are in US Mountain Standard Time
utc_transformer = CSVTransformer(
    timestamp_key="datetime",
    timezone_type="offset",
    timezone="-0700",
)

# IANA timezone — handles daylight saving time automatically
iana_transformer = CSVTransformer(
    timestamp_key="datetime",
    timezone_type="iana",
    timezone="America/Denver",
)

# Embedded offsets — timestamps include their own offset, e.g. "2024-01-15T08:30:00-07:00"
# Omit timezone_type (or set it to None) to read offsets from the timestamps directly.
transformer = CSVTransformer(
    timestamp_key="datetime",
)
```

UTC offsets must be in `±HHMM` or `±HH:MM` format with hours between `00` and `14` and minutes between `00` and `59`. IANA timezone names must be valid entries from the IANA Time Zone Database (e.g. `"America/Denver"`, `"Europe/London"`).

All timestamps are normalized to UTC before loading regardless of the source timezone configuration.

### Data Mappings

Data mappings connect source columns (by name or index) to HydroServer datastream IDs. Each mapping can fan out to multiple target datastreams, and optional data operations can be applied per target path.

```python
from hydroserverpy.etl.transformers import ETLDataMapping, ETLTargetPath

data_mappings = [
    ETLDataMapping(
        source_identifier="water_level",
        target_paths=[
            ETLTargetPath(target_identifier="<datastream-uuid-1>"),
        ],
    ),
    ETLDataMapping(
        source_identifier="discharge",
        target_paths=[
            ETLTargetPath(target_identifier="<datastream-uuid-2>"),
        ],
    ),
]
```

#### Data Operations

Target paths can include a sequence of data operations applied to the source values before loading. Operations are applied in order — the output of each becomes the input of the next. Supported operations are arithmetic expressions, rating curves, and temporal aggregation.

**Arithmetic expression** — applies a Python arithmetic expression where `x` represents the source value. Only `+`, `-`, `*`, `/`, numeric literals, and the variable `x` are permitted.

```python
from hydroserverpy.etl.transformers import ETLTargetPath
from hydroserverpy.etl.operations import ArithmeticExpressionOperation

ETLTargetPath(
    target_identifier="<datastream-uuid>",
    data_operations=[
        ArithmeticExpressionOperation(
            expression="(x - 32) / 1.8",   # Fahrenheit to Celsius
            target_identifier="<datastream-uuid>",
        )
    ],
)
```

**Rating curve** — maps input values to output values using linear interpolation against a CSV lookup table retrieved from a URL. The first two columns of the CSV are used as input and output values (the file should have a header row); rows that aren't numeric are ignored, and the table needs at least two numeric rows. Input values outside the table's range are set to `no_data_value` if you provide one, and left empty otherwise, rather than being clamped to the table's ends.

```python
from hydroserverpy.etl.transformers import ETLTargetPath
from hydroserverpy.etl.operations import RatingCurveDataOperation

ETLTargetPath(
    target_identifier="<datastream-uuid>",
    data_operations=[
        RatingCurveDataOperation(
            rating_curve_url="https://example.com/curves/stage-discharge.csv",
            no_data_value=-9999,
            target_identifier="<datastream-uuid>",
        )
    ],
)
```

**Temporal aggregation** — reduces per-observation values into period-level summaries. When included, it should be the last operation in the sequence, as it changes the shape of the data from one row per observation to one row per aggregation window.

```python
from hydroserverpy.etl.transformers import ETLTargetPath
from hydroserverpy.etl.operations import TemporalAggregationOperation

ETLTargetPath(
    target_identifier="<datastream-uuid>",
    data_operations=[
        TemporalAggregationOperation(
            aggregation_statistic="simple_mean",
            aggregation_interval=1,
            aggregation_interval_unit="day",
            target_identifier="<datastream-uuid>",
        )
    ],
)
```

Because temporal aggregation is a per-target operation, different targets fed by the same source can use different statistics, intervals, or timezone alignments independently.

#### Aggregation statistic

| `aggregation_statistic` | Behaviour |
|---|---|
| `"simple_mean"` | Arithmetic mean of all observations within the window. |
| `"time_weighted_mean"` | Mean weighted by the time between observations, computed via trapezoidal integration. Values at window boundaries are estimated by linear interpolation from the nearest surrounding observations. |
| `"last_value_of_period"` | The last observation within the window. |

#### Aggregation interval

`aggregation_interval` (integer, default `1`) and `aggregation_interval_unit` together define the window width. An `aggregation_interval` of `3` with unit `"day"` produces 3-day windows. `"day"` is currently the only supported unit; any other value is rejected when the operation is created.

#### Timezone

Window boundaries are aligned to local midnight in the configured timezone. The timezone fields follow the same conventions as the transformer timestamp configuration, with `None` (the default) falling back to UTC-day boundaries.

| `timezone_type` | Window boundary alignment | Requires |
|---|---|---|
| `None` (default) | UTC midnight | — |
| `"utc"` | UTC midnight | — |
| `"offset"` | Local midnight at a fixed UTC offset | `timezone` in `±HHMM` or `±HH:MM` format |
| `"iana"` | Local midnight in a named timezone, handling DST automatically | `timezone` as a valid IANA name |

```python
from hydroserverpy.etl.operations import TemporalAggregationOperation

# Daily windows aligned to US Mountain Time (UTC-7, DST-aware)
TemporalAggregationOperation(
    aggregation_statistic="simple_mean",
    aggregation_interval=1,
    aggregation_interval_unit="day",
    timezone_type="iana",
    timezone="America/Denver",
    target_identifier="<datastream-uuid>",
)

# Daily windows at a fixed offset (no DST adjustment)
TemporalAggregationOperation(
    aggregation_statistic="time_weighted_mean",
    aggregation_interval=1,
    aggregation_interval_unit="day",
    timezone_type="offset",
    timezone="-0700",
    target_identifier="<datastream-uuid>",
)
```

**Window boundary semantics:** Windows run from the local midnight that contains the first observation to the local midnight that contains the last observation. The last observation defines the exclusive upper boundary — observations on that final local day are not aggregated. Ensure your source data extends at least one day past the last period you want included, or that the last observation falls on the day following the final window.

Days with no observations are omitted from the output rather than filled with null values.

### Loader

```python
from hydroserverpy import HydroServer
from hydroserverpy.etl.loaders import HydroServerLoader

hs = HydroServer(host="https://playground.hydroserver.org", email="your@email.com", password="yourpassword")

loader = HydroServerLoader(
    client=hs,
    chunk_size=5000,   # number of observations to upload per request
)
```

The loader only writes observations that are newer than the most recent observation already in each target datastream. Running the same pipeline twice therefore doesn't duplicate data — on the second run, each target is reported as `skipped`. To reload or correct data you've already loaded, use a [data ingestion window](#reloading-a-time-window).

### Assembling the Pipeline

```python
from hydroserverpy.etl import ETLPipeline

pipeline = ETLPipeline(
    extractor=extractor,
    transformer=transformer,
    loader=loader,
)
```

## Running the Pipeline

Call `run()` with the data mappings and any template variables required by the extractor or transformer:

```python
context = pipeline.run(
    data_mappings=data_mappings,
    station_id="station-42",
)
```

By default, any exception will be re-raised immediately. Pass `raise_on_error=False` to instead capture the failure in the returned context and continue:

```python
context = pipeline.run(
    data_mappings=data_mappings,
    station_id="station-42",
    raise_on_error=False,
)
```

### Reloading a time window

Pass `data_ingestion_window_start` and/or `data_ingestion_window_end` (timezone-aware datetimes) to load only observations within that window. With a window set, the loader replaces each target's existing observations inside the window with the newly transformed ones, instead of skipping data that's already loaded — useful for backfilling or correcting a period.

```python
from datetime import datetime, timezone

context = pipeline.run(
    data_mappings=data_mappings,
    station_id="station-42",
    data_ingestion_window_start=datetime(2026, 5, 1, tzinfo=timezone.utc),
    data_ingestion_window_end=datetime(2026, 5, 8, tzinfo=timezone.utc),
)
```

Scheduled data connections configure their data ingestion window in the web app.

## Viewing Results

`run()` returns an `ETLContext` object describing the outcome of the run.

```python
from hydroserverpy.etl import ETLStatus, ETLStage

print(context.status)   # ETLStatus.SUCCESS, INCOMPLETE, or FAILED
print(context.stage)    # ETLStage where the run ended
```

`context.stage` is `CLEANUP` after a run that completed, or the stage that failed: `EXTRACT` (including missing template variables), `TRANSFORM`, or `LOAD`.

The `results` field holds an `ETLLoaderResult` with summary counts and per-target detail. It is `None` if the run failed before or during the load stage, so check it first:

```python
results = context.results
if results is None:
    raise SystemExit(f"Run failed during {context.stage}: {context.exception}")

print(results.success_count)       # number of datastreams successfully loaded
print(results.failure_count)       # number of datastreams that failed
print(results.skipped_count)       # number of datastreams with no new data
print(results.values_loaded_total) # total observations written across all datastreams
print(results.earliest_timestamp)  # earliest observation timestamp loaded
print(results.latest_timestamp)    # latest observation timestamp loaded
```

Per-target results are keyed by datastream ID:

```python
for target_id, target in results.target_results.items():
    print(target_id, target.status, target.values_loaded)
```

### Status values

| `ETLStatus`  | Meaning |
|---|---|
| `SUCCESS`    | The run completed and no target failed. This includes runs where every target was skipped because there was no new data. |
| `INCOMPLETE` | At least one target failed while uploading; others may have loaded successfully. |
| `FAILED`     | A stage raised an error. This includes the loader's check, before anything is uploaded, that every target datastream exists — a missing or invalid target fails the whole run. |
| `RUNNING`    | The pipeline is currently executing |
| `PENDING`    | The pipeline has not yet started |

## Debugging Errors

When `raise_on_error=False`, the exception that ended the run is available on the context:

```python
import traceback
from hydroserverpy.etl import ETLStatus

if context.status == ETLStatus.FAILED:
    print(context.stage)       # which stage failed
    print(context.exception)   # the error message
    traceback.print_exception(context.exception)  # full traceback
```

The context also records what happened during the run:

- `context.log_entries` — the run's log messages, each a dict with `timestamp`, `level`, `logger`, `stage`, and `message`.
- `context.runtime_variables` — the extractor, transformer, and loader settings after template variables were filled in, such as the resolved `source_uri`.

For partial failures where some datastreams loaded and others did not (`ETLStatus.INCOMPLETE`), inspect the per-target results:

```python
for target_id, target in context.results.target_results.items():
    if target.status == "failed":
        print(f"{target_id}: {target.error}")
        print(target.traceback)
```

### Common errors and causes

Errors raised during a run are translated into the messages below. The message is what you see in `context.exception` (or in the raised exception) and in HydroServer's task run history.

**Extract stage**

| Error message begins with | Likely cause |
|---|---|
| `The extractor URL includes a placeholder '...', but no value was supplied` | A `{variable}` in `source_uri` or `filepath` wasn't passed to `run()` |
| `Failed to connect to the source system` | The source is offline or unreachable, or the request timed out |
| `The requested data could not be found on the source system` | The URL or file path doesn't exist |
| `Authentication with the source system failed` | Credentials or auth headers are incorrect or expired |
| `No observations were returned from the source system` | The source returned an empty file or response |

**Transform stage**

| Error message begins with | Likely cause |
|---|---|
| `The column mapped as the timestamp does not exist in the file` | `timestamp_key` doesn't match any column in the CSV |
| `The timestamp column is set incorrectly. Index mode expects a 1-based column number` | `identifier_type="index"` with a `timestamp_key` that isn't a valid column number |
| `The CSV header or data start row is set incorrectly` | `header_row` or `data_start_row` doesn't match the file |
| `A required column was not found in the file header` | A mapped source column isn't present in the CSV header |
| `A mapping source index (...) is out of range for the extracted data` | An index-mode source identifier is larger than the number of columns |
| `A mapped field named '...' was not found in the extracted data` | A source identifier doesn't match any column or JSON field |
| `The source did not return valid JSON` | The extracted payload isn't JSON |
| `The JSON query used to extract timestamps or values is invalid` | The `jmespath` expression has a syntax error |
| `Failed to find the timestamp or value using the current JSON query` / `The job could not find the expected timestamp or value fields` | The `jmespath` expression doesn't match the payload, or the selected records lack `timestamp_key` |
| `A custom timestamp format is required when the timestamp type is set to custom` | `timestamp_type="custom"` without `timestamp_format` |
| `The custom timestamp format is not valid` | `timestamp_format` isn't a valid strftime string |
| `The timestamp UTC offset is not valid` | `timezone` isn't in `±HHMM` or `±HH:MM` format |
| `The configured timezone is not recognized` | `timezone` isn't a valid IANA name |
| `Timezone information should not be provided when the timestamps already include their own timezone values` | A `timezone` was set for timestamps that already include an offset |
| `Failed to compile arithmetic expression for data target` | An expression contains unsupported syntax or variables other than `x` |

A `jmespath` expression that selects an empty list isn't an error: the run completes with `SUCCESS`, nothing is loaded, and `results.target_results` is empty.

**Load stage**

| Error message begins with | Likely cause |
|---|---|
| `One or more destination datastream identifiers could not be found in HydroServer` | A `target_identifier` isn't the UUID of an existing datastream, or your account can't access it |
| `HydroServer rejected the load due to authorization` | Your account doesn't have permission to write to the target datastream |
| `HydroServer rejected some or all of the data` | Invalid timestamps or values were sent to a datastream |
