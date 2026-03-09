# Overview of the `hydroserverpy.etl` Package

The `hydroserverpy.etl` package provides a framework for building Extract, Transform, and Load (ETL) pipelines that move time series data from external sources into a HydroServer instance. This guide covers how to configure a pipeline, run it, interpret results, and debug errors.

---

## Overview

A pipeline is made up of three components:

- An **Extractor** that retrieves raw data from a source (HTTP, FTP, or local file).
- A **Transformer** that parses the raw data into a standardized Pandas DataFrame.
- A **Loader** that writes the transformed observations to HydroServer datastreams.

These are assembled into an `ETLPipeline` and executed with a set of data mappings that describe which source columns map to which HydroServer datastream targets.

---

## Configuring a Pipeline

### Extractors

Extractors retrieve data from a source and return a file-like object. The `source_uri` field supports template variables, which are resolved at runtime using keyword arguments passed to `run()`.

**HTTP:**
```python
from hydroserverpy.etl.extractors import HTTPExtractor

extractor = HTTPExtractor(
    source_uri="https://api.example.com/data/{station_id}/export.csv"
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

Transformers parse the extracted payload into a DataFrame with columns `timestamp`, `value`, and `target_id`.

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

The `jmespath` expression selects the array of records from the JSON payload. Since JMESPath can rename fields natively, the timestamp column in the selected records must be named to match `timestamp_key`, or renamed in the expression itself.

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

**Rating curve** — maps input values to output values using linear interpolation against a two-column CSV lookup table (input, output), retrieved from a URL.

```python
from hydroserverpy.etl.transformers import ETLTargetPath
from hydroserverpy.etl.operations import RatingCurveDataOperation

ETLTargetPath(
    target_identifier="<datastream-uuid>",
    data_operations=[
        RatingCurveDataOperation(
            rating_curve_url="https://example.com/curves/stage-discharge.csv",
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

`aggregation_interval` (integer, default `1`) and `aggregation_interval_unit` (currently `"day"`) together define the window width. An `aggregation_interval` of `3` with unit `"day"` produces 3-day windows.

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

hs = HydroServer(host="https://playground.hydroserver.org", email="user@example.com", password="pass")

loader = HydroServerLoader(
    client=hs,
    chunk_size=5000,   # number of observations to upload per request
)
```

### Assembling the Pipeline

```python
from hydroserverpy.etl import ETLPipeline

pipeline = ETLPipeline(
    extractor=extractor,
    transformer=transformer,
    loader=loader,
)
```

---

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

---

## Viewing Results

`run()` returns an `ETLContext` object describing the outcome of the run.

```python
print(context.status)   # ETLStatus.SUCCESS, FAILED, INCOMPLETE, etc.
print(context.stage)    # ETLStage where the run ended: EXTRACT, TRANSFORM, LOAD
```

The `results` field holds an `ETLLoaderResult` with summary counts and per-target detail:

```python
results = context.results

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
| `SUCCESS`    | All datastreams loaded without error |
| `INCOMPLETE` | At least one datastream failed or was skipped |
| `FAILED`     | The pipeline did not reach the load stage |
| `RUNNING`    | The pipeline is currently executing |
| `PENDING`    | The pipeline has not yet started |

---

## Debugging Errors

When `raise_on_error=False`, failure details are available on the context:

```python
if context.status == ETLStatus.FAILED:
    print(context.error)      # exception message
    print(context.traceback)  # full traceback string
    print(context.stage)      # which stage failed: EXTRACT, TRANSFORM, or LOAD
```

For partial failures where some datastreams loaded and others did not (`ETLStatus.INCOMPLETE`), inspect the per-target results:

```python
for target_id, target in context.results.target_results.items():
    if target.status == "failed":
        print(f"{target_id}: {target.error}")
        print(target.traceback)
```

### Common errors and causes

**Extract stage**

| Error | Likely cause |
|---|---|
| `... not found` | The source URI resolved to a path or URL that doesn't exist |
| `... timed out` | The source system did not respond in time |
| `Authentication ... failed` | Credentials are incorrect or expired |
| `... is empty` | The source returned a file with no content |
| `Missing required runtime variables` | A template variable in `source_uri` or `filepath` was not passed to `run()` |

**Transform stage**

| Error | Likely cause |
|---|---|
| `Column ... not found` | `timestamp_key` or a source identifier doesn't match any column in the payload |
| `... empty CSV file` | The extracted file contained no parseable rows |
| `One or more configured CSV columns were not found` | A named source identifier isn't present in the CSV header |
| `... not valid JSON` | The extracted payload is not valid JSON |
| `... could not be found with the specified query` | The JMESPath expression returned no results |
| `Failed to compile arithmetic expression` | An expression contains unsupported syntax or variables other than `x` |

**Load stage**

| Error | Likely cause |
|---|---|
| `Missing datastream IDs: ...` | One or more target datastream UUIDs don't exist on the HydroServer instance |
| `HydroServer loader failed to retrieve datastream` | A network or authentication error occurred while looking up a datastream |