# Loading Data into HydroServer with Hydroserverpy

This guide explains how to use the `hydroserverpy` Python library to automatically load data from external web sources into HydroServer. You'll configure two things:

- A **data connection** - describes where your data comes from, what format it's in, and how to read timestamps.
- A **data ingestion task** - connects that source to one or more of your HydroServer datastreams, and defines when the loading should happen.

Once configured, HydroServer runs the tasks on your schedule and loads new observations automatically. You can also trigger tasks on demand and check the results of each run.

## Before You Begin

Make sure you have `hydroserverpy` installed:

```bash
pip install hydroserverpy
```

You will also need:

- A HydroServer account (email/password or API key)
- The ID of the **workspace** where your datastreams live
- The IDs of the **datastreams** you want to load data into

You can find workspace and datastream IDs in the HydroServer web interface, or by listing them with hydroserverpy:

```python
from hydroserverpy import HydroServer

hs_api = HydroServer(
    host="https://your-hydroserver.org",
    email="you@example.com",
    password="your-password",
)

# List your workspaces
for workspace in hs_api.workspaces.list(is_associated=True).items:
    print(workspace.uid, workspace.name)

# List datastreams in a workspace
for ds in hs_api.datastreams.list(workspace="your-workspace-id").items:
    print(ds.uid, ds.name)
```

## Connect to HydroServer

All hydroserverpy operations start by creating a connection to your HydroServer instance. You can authenticate with an email and password:

```python
from hydroserverpy import HydroServer

hs_api = HydroServer(
    host="https://your-hydroserver.org",
    email="you@example.com",
    password="your-password",
)
```

Or with an API key if you have one:

```python
hs_api = HydroServer(
    host="https://your-hydroserver.org",
    apikey="your-api-key",
)
```

## Step 1: Create a Data Connection

A data connection tells HydroServer:

- **Where** to fetch data (a URL)
- **What format** the data comes in (CSV or JSON)
- **How to read timestamps** (which column/field contains the time, and what format it's in)

Data connections are reusable - multiple tasks can share the same connection. If you load data from the same source into different datastreams, you only need one data connection.

### CSV Data Connection

Use this when your data source returns a CSV file. The example below loads from a URL that accepts a `start_date` query parameter:

```python
data_connection = hs_api.dataconnections.create(
    name="My CSV Source",
    workspace="your-workspace-id",
    source_url="https://api.example.com/readings.csv?start={start_date}",
    timestamp_key="Timestamp",
    payload_type="CSV",
    description="Hourly sensor readings.",
    timestamp_format="%Y-%m-%d %H:%M:%S",
    timezone_type="utc",
    header_row=1,
    data_start_row=2,
    delimiter=",",
    placeholder_variables=[
        {
            "name": "start_date",
            "variable_type": "latest_observation_timestamp",
            "timestamp_format": "%Y-%m-%dT%H:%M:%S",
        },
    ],
)
```

**CSV-specific options:**

| Option           | What it does                                                                     |
| ---------------- | -------------------------------------------------------------------------------- |
| `timestamp_key`  | The column header that contains timestamps.                                      |
| `header_row`     | The row number of the column headers (usually `1`).                              |
| `data_start_row` | The first row of actual data (usually `2`).                                      |
| `delimiter`      | The character separating columns. Supported: comma, pipe, tab, semicolon, space. |

### JSON Data Connection

Use this when your data source returns a JSON response. The `jmespath` option lets you point to the array of records inside the JSON structure:

```python
data_connection = hs_api.dataconnections.create(
    name="My JSON Source",
    workspace="your-workspace-id",
    source_url="https://api.example.com/readings.json",
    timestamp_key="datetime",
    payload_type="JSON",
    jmespath="data[*]",
)
```

The `jmespath` expression selects the list of records from the response. The records must contain the field named by `timestamp_key`. For example, if the JSON response looks like this:

```json
{
  "data": [
    { "datetime": "2024-01-01T00:00:00Z", "temperature": 22.5 },
    { "datetime": "2024-01-01T01:00:00Z", "temperature": 22.8 }
  ]
}
```

Then `jmespath="data[*]"` and `timestamp_key="datetime"` would work correctly.

### Timestamp Settings

Every data connection needs to know which field contains timestamps and how they are formatted.

**`timestamp_key`** is required - it names the column (CSV) or field (JSON) that holds the timestamp.

**`timestamp_format`** is optional but recommended if your timestamps are not standard ISO 8601 format. Use Python `strftime` syntax:

| Format string          | Parses timestamps like |
| ---------------------- | ---------------------- |
| `"%Y-%m-%d %H:%M:%S"`  | `2024-01-15 08:30:00`  |
| `"%m/%d/%Y %I:%M %p"`  | `01/15/2024 08:30 AM`  |
| `"%Y-%m-%dT%H:%M:%SZ"` | `2024-01-15T08:30:00Z` |

**`timezone_type`** tells HydroServer how to interpret timestamps that don't include timezone information:

| `timezone_type` | Behavior                                                                   |
| --------------- | -------------------------------------------------------------------------- |
| _(not set)_     | Use whatever timezone information is embedded in the timestamp, if any.    |
| `"utc"`         | Treat timestamps as UTC.                                                   |
| `"offset"`      | Apply a fixed UTC offset (e.g. `"-0700"`), set via `timezone`.             |
| `"iana"`        | Apply an IANA timezone name (e.g. `"America/Denver"`), set via `timezone`. |

For example, to treat timestamps as Mountain Time (US):

```python
data_connection = hs_api.dataconnections.create(
    name="Mountain Time Source",
    workspace="your-workspace-id",
    source_url="https://api.example.com/readings.csv",
    timestamp_key="Time",
    payload_type="CSV",
    timezone_type="iana",
    timezone="America/Denver",
)
```

### URL Placeholders

If your data source requires parameters in the URL - such as a date range or station identifier - you can define these as **placeholders** in `source_url` and then describe how each placeholder should be filled in.

Placeholders are written as `{name}` in the URL. For example:

```
https://api.example.com/{station_id}/data.csv?start={start_date}
```

Each placeholder needs a matching entry in `placeholder_variables` with a `variable_type`:

| `variable_type`                  | What value is used                                                                                                                                       |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `"latest_observation_timestamp"` | The oldest "latest observation" timestamp across all mapped target datastreams. Useful for incremental loading - only fetch data you don't already have. |
| `"run_time"`                     | The time the task started running.                                                                                                                       |
| `"per_task"`                     | A custom value you set directly on each task (via `task_variables`). Use this for things like station IDs that differ per task.                          |

For `"latest_observation_timestamp"` and `"run_time"`, you can also specify a `timestamp_format` to control how the datetime is formatted in the URL.

**Example - loading only new data using the latest observation timestamp:**

```python
data_connection = hs_api.dataconnections.create(
    name="Incremental CSV Source",
    workspace="your-workspace-id",
    source_url="https://api.example.com/data.csv?start={start_date}",
    timestamp_key="Timestamp",
    payload_type="CSV",
    placeholder_variables=[
        {
            "name": "start_date",
            "variable_type": "latest_observation_timestamp",
            "timestamp_format": "%Y-%m-%dT%H:%M:%S",
        },
    ],
)
```

**Example - per-task station ID combined with a run-time date:**

```python
data_connection = hs_api.dataconnections.create(
    name="Station API",
    workspace="your-workspace-id",
    source_url="https://api.example.com/{station_id}?as_of={run_time}",
    timestamp_key="timestamp",
    payload_type="JSON",
    jmespath="observations[*]",
    placeholder_variables=[
        {"name": "station_id", "variable_type": "per_task"},
        {
            "name": "run_time",
            "variable_type": "run_time",
            "timestamp_format": "%Y-%m-%dT%H:%M:%S",
        },
    ],
)
```

When you use `"per_task"` placeholders, each task provides its own value for that variable (see [Create a Task](#step-2-create-a-data-ingestion-task) below).

### Email Notifications

You can configure a data connection to send email summaries to one or more recipients on a schedule:

```python
data_connection = hs_api.dataconnections.create(
    name="Notified Source",
    workspace="your-workspace-id",
    source_url="https://api.example.com/readings.csv",
    timestamp_key="Timestamp",
    payload_type="CSV",
    notification={
        "recipient_emails": ["admin@example.com", "engineer@example.com"],
        "schedule": {
            "enabled": True,
            "interval": 1,
            "interval_period": "days",
        },
    },
)
```

`interval_period` can be `"minutes"`, `"hours"`, or `"days"`.

## Step 2: Create a Data Ingestion Task

A task connects a data connection to your HydroServer datastreams. It specifies:

- Which **data connection** to use
- How **fields in the source data** map to **target datastreams** (the `mappings`)
- **When** to run (on a schedule, or manually)
- Any **per-task variable values** for URL placeholders

### Field Mappings

A mapping pairs a `source_identifier` with a `target_datastream_id`. The `source_identifier` is the column name (for CSV) or field name (for JSON) in the data returned by your source URL. The `target_datastream_id` is the UUID of the HydroServer datastream you want to load that data into.

If you're unsure what field names your source returns, you can inspect a sample response from your source URL in a browser or with a tool like `curl`.

### Create a Basic Task

```python
task = hs_api.tasks.create(
    name="Hourly Temperature and Humidity",
    data_connection=data_connection.uid,
    description="Loads hourly readings from the station API.",
    mappings=[
        {
            "source_identifier": "Temperature",
            "target_datastream_id": "your-temperature-datastream-id",
        },
        {
            "source_identifier": "Humidity",
            "target_datastream_id": "your-humidity-datastream-id",
        },
    ],
    interval=1,
    interval_period="hours",
    enabled=True,
)
```

### Per-Task Variables

If your data connection uses `"per_task"` placeholders, provide the values in `task_variables`. The key must match the placeholder name:

```python
task = hs_api.tasks.create(
    name="Station 42 Temperature",
    data_connection=data_connection.uid,
    task_variables={
        "station_id": "station-42",
    },
    mappings=[
        {
            "source_identifier": "Temperature",
            "target_datastream_id": "your-datastream-id",
        },
    ],
    interval=1,
    interval_period="hours",
    enabled=True,
)
```

### Task Scheduling

Tasks can run on an **interval schedule**, a **crontab schedule**, or not at all (manual trigger only).

**Interval schedule** - run every N minutes, hours, or days:

```python
# Run every 15 minutes
task = hs_api.tasks.create(
    name="15-Minute Ingestion",
    data_connection=data_connection.uid,
    mappings=[...],
    interval=15,
    interval_period="minutes",
    enabled=True,
)

# Run every 6 hours
task = hs_api.tasks.create(
    name="Six-Hour Ingestion",
    data_connection=data_connection.uid,
    mappings=[...],
    interval=6,
    interval_period="hours",
    enabled=True,
)

# Run once a day
task = hs_api.tasks.create(
    name="Daily Ingestion",
    data_connection=data_connection.uid,
    mappings=[...],
    interval=1,
    interval_period="days",
    enabled=True,
)
```

**Crontab schedule** - run at a specific time, using standard cron syntax:

```python
# Run every day at 2:00 AM UTC
task = hs_api.tasks.create(
    name="Nightly Ingestion",
    data_connection=data_connection.uid,
    mappings=[...],
    crontab="0 2 * * *",
    enabled=True,
)
```

Crontab format is `minute hour day-of-month month day-of-week`. Common examples:

| Crontab          | Runs at                           |
| ---------------- | --------------------------------- |
| `"0 * * * *"`    | Every hour at the top of the hour |
| `"*/15 * * * *"` | Every 15 minutes                  |
| `"0 8 * * *"`    | Every day at 8:00 AM UTC          |
| `"0 0 * * 1"`    | Every Monday at midnight UTC      |

**No schedule (manual only)** - omit both `interval` and `crontab`:

```python
task = hs_api.tasks.create(
    name="Manual Ingestion",
    data_connection=data_connection.uid,
    mappings=[...],
)
```

You can also set a `start_time` to delay when a scheduled task first runs:

```python
from datetime import datetime, timezone

task = hs_api.tasks.create(
    name="Delayed Start Task",
    data_connection=data_connection.uid,
    mappings=[...],
    interval=1,
    interval_period="days",
    start_time=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
    enabled=True,
)
```

## Step 3: Run a Task

### Trigger a Task Manually

You can start an immediate run at any time, regardless of schedule:

```python
task = hs_api.tasks.get(uid="your-task-id")
task_run = task.trigger()

print(task_run.status)   # Usually "PENDING" right after triggering
print(task_run.id)       # The ID of this run, for looking it up later
```

### Check Run Status

Task runs go through the following statuses:

| Status    | Meaning                         |
| --------- | ------------------------------- |
| `PENDING` | The run has been queued.        |
| `STARTED` | The run is in progress.         |
| `SUCCESS` | The run completed successfully. |
| `FAILURE` | The run failed.                 |

To check the current status of a run you triggered:

```python
run = task.get_run(run_id=task_run.id)
print(run.status)
print(run.message)   # Human-readable summary or error message
print(run.result)    # Detailed result information (dict), if available
```

## Viewing Run History

You can browse the history of all runs for a task to see what succeeded, what failed, and when.

```python
from datetime import datetime, timezone

task = hs_api.tasks.get(uid="your-task-id")

# Get the 10 most recent runs, newest first
recent_runs = task.list_runs(order_by=["-started_at"], page_size=10)
for run in recent_runs:
    print(run.started_at, run.status, run.message)

# Filter to only failed runs
failed_runs = task.list_runs(status="FAILURE")

# Filter to runs that started after a certain date
runs_since_jan = task.list_runs(
    started_at_min=datetime(2025, 1, 1, tzinfo=timezone.utc),
)

# Get a single run by ID
run = task.get_run(run_id="your-run-id")
print(run.status, run.result)
```

A task run has these fields:

| Field         | Description                                               |
| ------------- | --------------------------------------------------------- |
| `id`          | Unique ID of this run.                                    |
| `status`      | `PENDING`, `STARTED`, `SUCCESS`, or `FAILURE`.            |
| `message`     | Summary message or error description.                     |
| `result`      | Detailed result data (observations loaded, errors, etc.). |
| `started_at`  | When the run started.                                     |
| `finished_at` | When the run finished.                                    |

## Managing Data Connections

### List Data Connections

```python
# Get the first page of data connections
data_connections = hs_api.dataconnections.list()
for dc in data_connections.items:
    print(dc.uid, dc.name)

# Get all data connections at once
all_connections = hs_api.dataconnections.list(fetch_all=True)

# Filter by workspace
workspace_connections = hs_api.dataconnections.list(
    workspace="your-workspace-id",
)

# Filter by payload type
csv_connections = hs_api.dataconnections.list(payload_type="CSV")
json_connections = hs_api.dataconnections.list(payload_type="JSON")
```

### Get a Specific Data Connection

```python
data_connection = hs_api.dataconnections.get(uid="your-connection-id")
print(data_connection.name)
print(data_connection.source_url)
print(data_connection.payload.payload_type)  # "CSV" or "JSON"
```

### Update a Data Connection

Change any properties directly on the object, then call `.save()`:

```python
data_connection = hs_api.dataconnections.get(uid="your-connection-id")

data_connection.name = "Updated Name"
data_connection.source_url = "https://api.example.com/new-endpoint.csv"
data_connection.save()
```

### Delete a Data Connection

```python
data_connection = hs_api.dataconnections.get(uid="your-connection-id")
data_connection.delete()
```

## Managing Tasks

### List Tasks

```python
# Get all tasks
tasks = hs_api.tasks.list()

# Filter by workspace
workspace_tasks = hs_api.tasks.list(workspace="your-workspace-id")

# Filter by data connection
connection_tasks = hs_api.tasks.list(
    data_connection="your-connection-id",
)

# Filter by the status of the last run
failed_tasks = hs_api.tasks.list(latest_run_status="FAILURE")
successful_tasks = hs_api.tasks.list(latest_run_status="SUCCESS")
```

### Get a Specific Task

```python
task = hs_api.tasks.get(uid="your-task-id")
print(task.name)
print(task.enabled)
print(task.interval, task.interval_period)
print(task.latest_run.status if task.latest_run else "No runs yet")
```

### Update a Task

```python
task = hs_api.tasks.get(uid="your-task-id")

task.name = "Updated Task Name"
task.description = "New description."
task.task_variables["station_id"] = "station-99"
task.enabled = False  # Pause the task
task.save()
```

When you save a task, HydroServer updates the name, description, task variables, mappings, and schedule.

### Delete a Task

```python
task = hs_api.tasks.get(uid="your-task-id")
task.delete()
```

## Troubleshooting

| Symptom                                                                   | What to check                                                                                                                                                                      |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Task runs but no observations are loaded                                  | Make sure each mapping's `source_identifier` exactly matches a column header (CSV) or field name (JSON) in the source data. Field names are case-sensitive.                        |
| JSON task loads no records                                                | Verify the `jmespath` expression selects the list of records. Try testing it at [jmespath.org](https://jmespath.org).                                                              |
| Timestamps are shifted by several hours                                   | Check `timezone_type` and `timezone`. If your source returns timestamps in local time without timezone info, you need to tell HydroServer the timezone.                            |
| Timestamps fail to parse                                                  | Check `timestamp_key` and `timestamp_format`. Make sure the format string matches the actual timestamp format in your source.                                                      |
| URL placeholder is not being filled in                                    | Every `{name}` in `source_url` must have a matching entry in `placeholder_variables`. For `"per_task"` placeholders, the same key must also appear in the task's `task_variables`. |
| Task has `"per_task"` placeholder but `task_variables` is missing the key | Add the missing key to `task_variables` when creating or updating the task.                                                                                                        |
| Task never runs automatically                                             | Make sure `enabled=True` and that the task has either an `interval` + `interval_period`, or a `crontab` value.                                                                     |
| Authentication error                                                      | Check that your email, password, or API key is correct, and that your account has permission to access the workspace.                                                              |
