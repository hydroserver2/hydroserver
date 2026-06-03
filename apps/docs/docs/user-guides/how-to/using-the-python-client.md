# Python Client Reference — hydroserverpy

`hydroserverpy` is HydroServer's official Python client library. This page is a reference for the classes, properties, and methods it exposes. If you're new to the library, start with the [Getting Started with hydroserverpy](/user-guides/tutorials/getting-started-with-hydroserverpy/) tutorial series.

---

## Connection

```python
from hydroserverpy import HydroServer

# Email/password authentication
hs_api = HydroServer(host, email, password)

# API key authentication
hs_api = HydroServer(host, apikey=apikey)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `host` | `str` | — | Base URL of your HydroServer instance |
| `email` | `str` | `None` | Account email |
| `password` | `str` | `None` | Account password |
| `apikey` | `str` | `None` | API key (alternative to email/password) |

**Methods**

| Method | Description |
|---|---|
| `login(email, password)` | Re-authenticate with new credentials without creating a new instance |
| `logout()` | End the current session |

---

## Common Patterns

### HydroServerCollection

`list()` methods return a `HydroServerCollection` rather than a plain list.

| Property | Type | Description |
|---|---|---|
| `items` | `List[T]` | The resources on the current page |
| `page` | `int` | Current page number (1-indexed) |
| `page_size` | `int` | Number of items per page |
| `total_pages` | `int` | Total number of pages |
| `total_count` | `int` | Total number of matching resources |

| Method | Returns | Description |
|---|---|---|
| `next_page()` | `HydroServerCollection` | Fetch the next page |
| `previous_page()` | `HydroServerCollection \| None` | Fetch the previous page |
| `fetch_all()` | `HydroServerCollection` | Merge all pages into a single collection |

### Common list() parameters

All `list()` methods accept these parameters in addition to any entity-specific filters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | `int` | `1` | Page number to fetch |
| `page_size` | `int` | `100` | Results per page |
| `order_by` | `List[str]` | `[]` | Fields to sort by; prefix with `-` for descending |
| `fetch_all` | `bool` | `False` | If `True`, fetches and merges all pages automatically |

### Model methods

All resource objects share these methods inherited from `HydroServerBaseModel`:

| Method | Description |
|---|---|
| `save()` | Persist any modified editable fields back to HydroServer |
| `refresh()` | Re-fetch this resource's data from HydroServer |
| `delete()` | Delete this resource from HydroServer and set `uid` to `None` |

`save()` only sends fields listed in the **editable** column of each entity's property table. Read-only fields are never sent. Fields marked **computed** are lazy-loaded properties — they trigger an API call on first access and are then cached on the object.

### TaskRun

Returned by `trigger()` and `list_runs()` across ETL tasks, data product tasks, and monitoring tasks.

| Property | Type | Description |
|---|---|---|
| `id` | `UUID` | Run identifier |
| `status` | `str` | `"PENDING"`, `"STARTED"`, `"SUCCESS"`, or `"FAILURE"` |
| `message` | `str \| None` | Human-readable status message |
| `result` | `dict \| None` | Detailed result payload |
| `started_at` | `datetime \| None` | When the run started |
| `finished_at` | `datetime \| None` | When the run finished |

---

## Workspaces

**Property:** `hs_api.workspaces`

### Workspace properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `is_private` | `bool` | Yes | |
| `owner` | `Account` | No | See Account fields below |
| `collaborators` | `List[Collaborator]` | No | Computed |
| `apikeys` | `List[APIKey]` | No | Computed |
| `roles` | `List[Role]` | No | Computed |
| `things` | `List[Thing]` | No | Computed |
| `observedproperties` | `List[ObservedProperty]` | No | Computed |
| `units` | `List[Unit]` | No | Computed |
| `processinglevels` | `List[ProcessingLevel]` | No | Computed |
| `sensors` | `List[Sensor]` | No | Computed |
| `dataconnections` | `List[DataConnection]` | No | Computed |
| `tasks` | `List[EtlTask]` | No | Computed; ETL tasks only |

**Account fields** (accessible via `workspace.owner`):

| Field | Type |
|---|---|
| `name` | `str` |
| `email` | `str` |
| `organization_name` | `str \| None` |
| `phone` | `str \| None` |
| `address` | `str \| None` |
| `link` | `str \| None` |
| `user_type` | `str` |

**Collaborator fields** (items in `workspace.collaborators`):

| Field | Type | Notes |
|---|---|---|
| `uid` | `UUID` | |
| `user` | `Account` | The collaborator's account info |
| `role_id` | `UUID` | |
| `workspace_id` | `UUID` | |
| `role` | `Role` | Computed; also settable via assignment |
| `workspace` | `Workspace` | Computed |

**APIKey fields** (items in `workspace.apikeys`):

| Field | Type | Editable |
|---|---|---|
| `uid` | `UUID` | No |
| `name` | `str` | Yes |
| `description` | `str \| None` | Yes |
| `role_id` | `UUID` | Yes |
| `workspace_id` | `UUID` | No |
| `is_active` | `bool` | Yes |
| `expires_at` | `datetime \| None` | Yes |

`APIKey` objects support `save()`, `refresh()`, `delete()`, and `regenerate()` (invalidates the old key and returns a new key string).

### Service methods

```python
hs_api.workspaces.list(is_associated=None, is_private=None) -> HydroServerCollection[Workspace]
hs_api.workspaces.get(uid) -> Workspace
hs_api.workspaces.create(name, is_private=False) -> Workspace
```

| Filter | Type | Description |
|---|---|---|
| `is_associated` | `bool` | Only return workspaces you're a member of |
| `is_private` | `bool` | Filter by privacy setting |

### Workspace methods

| Method | Description |
|---|---|
| `add_collaborator(email, role)` | Add a user as a collaborator; `role` accepts a UUID string or Role object |
| `edit_collaborator_role(email, role)` | Change an existing collaborator's role |
| `remove_collaborator(email)` | Remove a collaborator |
| `transfer_ownership(email)` | Initiate an ownership transfer to another user |
| `accept_ownership_transfer()` | Accept a pending incoming ownership transfer |
| `cancel_ownership_transfer()` | Cancel a pending outgoing ownership transfer |
| `create_api_key(name, role, description=None, is_active=True, expires_at=None)` | Create a new API key; returns `(APIKey, key_string)` where `key_string` is the raw key value — store it, it won't be shown again |
| `delete_api_key(api_key_id)` | Delete an API key by its UUID |

---

## Things (Sites)

**Property:** `hs_api.things`

### Thing properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `description` | `str` | Yes | |
| `sampling_feature_type` | `str` | Yes | |
| `sampling_feature_code` | `str` | Yes | |
| `site_type` | `str` | Yes | |
| `data_disclaimer` | `str \| None` | Yes | |
| `is_private` | `bool` | Yes | |
| `latitude` | `float` | Yes | |
| `longitude` | `float` | Yes | |
| `elevation_m` | `float \| None` | Yes | |
| `elevation_datum` | `str \| None` | Yes | |
| `admin_area_1` | `str \| None` | Yes | State/province |
| `admin_area_2` | `str \| None` | Yes | County/district |
| `country` | `str \| None` | Yes | ISO 3166-1 alpha-2 |
| `workspace_id` | `UUID` | No | |
| `tags` | `Dict[str, str]` | No | Use tag methods to modify |
| `file_attachments` | `Dict[str, dict]` | No | Use attachment methods to modify |
| `workspace` | `Workspace` | No | Computed |
| `datastreams` | `List[Datastream]` | No | Computed |

### Service methods

```python
hs_api.things.list(workspace=None, bbox=None, site_type=None, sampling_feature_type=None,
                   tag=None, is_private=None) -> HydroServerCollection[Thing]
hs_api.things.get(uid) -> Thing
hs_api.things.create(workspace, name, description, sampling_feature_type, sampling_feature_code,
                     site_type, is_private, latitude, longitude, elevation_m=None,
                     elevation_datum=None, admin_area_1=None, admin_area_2=None,
                     country=None, data_disclaimer=None, uid=None) -> Thing
```

| Filter | Type | Description |
|---|---|---|
| `workspace` | `UUID \| str` | Filter by workspace |
| `bbox` | `tuple` | `(min_lon, min_lat, max_lon, max_lat)` bounding box |
| `site_type` | `str` | Filter by site type |
| `sampling_feature_type` | `str` | Filter by sampling feature type |
| `tag` | `tuple` | `(key, value)` filter by tag |
| `is_private` | `bool` | Filter by privacy setting |

### Tag and file attachment methods

| Method | Description |
|---|---|
| `add_tag(key, value)` | Add a tag to this thing |
| `update_tag(key, value)` | Update an existing tag's value |
| `delete_tag(key)` | Remove a tag |
| `add_file_attachment(file, file_attachment_type)` | Upload a file; `file` is an open binary file object |
| `delete_file_attachment(name)` | Remove a file attachment by filename |

---

## Metadata

Sensors, observed properties, units, processing levels, and result qualifiers all follow the same shape: a small set of editable fields, a read-only `workspace_id`, and a computed `workspace` property. They all support the standard `save()`, `refresh()`, and `delete()` model methods.

### Sensors

**Property:** `hs_api.sensors`

| Property | Type | Editable |
|---|---|---|
| `uid` | `UUID` | No |
| `name` | `str` | Yes |
| `description` | `str` | Yes |
| `encoding_type` | `str` | Yes |
| `manufacturer` | `str \| None` | Yes |
| `sensor_model` | `str \| None` | Yes |
| `sensor_model_link` | `str \| None` | Yes |
| `method_type` | `str` | Yes |
| `method_link` | `str \| None` | Yes |
| `method_code` | `str \| None` | Yes |
| `workspace_id` | `UUID \| None` | No |
| `workspace` | `Workspace \| None` | No | Computed |

```python
hs_api.sensors.list(workspace=None) -> HydroServerCollection[Sensor]
hs_api.sensors.get(uid) -> Sensor
hs_api.sensors.create(workspace, name, description, encoding_type, method_type,
                      manufacturer=None, sensor_model=None, sensor_model_link=None,
                      method_link=None, method_code=None, uid=None) -> Sensor
```

### Observed Properties

**Property:** `hs_api.observedproperties`

| Property | Type | Editable |
|---|---|---|
| `uid` | `UUID` | No |
| `name` | `str` | Yes |
| `definition` | `str` | Yes |
| `description` | `str` | Yes |
| `observed_property_type` | `str` | Yes |
| `code` | `str` | Yes |
| `workspace_id` | `UUID \| None` | No |
| `workspace` | `Workspace \| None` | No | Computed |

```python
hs_api.observedproperties.list(workspace=None) -> HydroServerCollection[ObservedProperty]
hs_api.observedproperties.get(uid) -> ObservedProperty
hs_api.observedproperties.create(workspace, name, definition, description,
                                 observed_property_type, code, uid=None) -> ObservedProperty
```

### Units

**Property:** `hs_api.units`

| Property | Type | Editable |
|---|---|---|
| `uid` | `UUID` | No |
| `name` | `str` | Yes |
| `symbol` | `str` | Yes |
| `definition` | `str` | Yes |
| `unit_type` | `str` | Yes |
| `workspace_id` | `UUID \| None` | No |
| `workspace` | `Workspace \| None` | No | Computed |

```python
hs_api.units.list(workspace=None) -> HydroServerCollection[Unit]
hs_api.units.get(uid) -> Unit
hs_api.units.create(workspace, name, symbol, definition, unit_type, uid=None) -> Unit
```

### Processing Levels

**Property:** `hs_api.processinglevels`

| Property | Type | Editable |
|---|---|---|
| `uid` | `UUID` | No |
| `code` | `str` | Yes |
| `definition` | `str \| None` | Yes |
| `explanation` | `str \| None` | Yes |
| `workspace_id` | `UUID \| None` | No |
| `workspace` | `Workspace \| None` | No | Computed |

```python
hs_api.processinglevels.list(workspace=None) -> HydroServerCollection[ProcessingLevel]
hs_api.processinglevels.get(uid) -> ProcessingLevel
hs_api.processinglevels.create(workspace, code, definition=None, explanation=None, uid=None) -> ProcessingLevel
```

### Result Qualifiers

**Property:** `hs_api.resultqualifiers`

| Property | Type | Editable |
|---|---|---|
| `uid` | `UUID` | No |
| `code` | `str` | Yes |
| `description` | `str` | Yes |
| `workspace_id` | `UUID \| None` | No |
| `workspace` | `Workspace \| None` | No | Computed |

```python
hs_api.resultqualifiers.list(workspace=None) -> HydroServerCollection[ResultQualifier]
hs_api.resultqualifiers.get(uid) -> ResultQualifier
hs_api.resultqualifiers.create(workspace, code, description, uid=None) -> ResultQualifier
```

---

## Datastreams

**Property:** `hs_api.datastreams`

### Datastream properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `description` | `str` | Yes | |
| `observation_type` | `str` | Yes | |
| `sampled_medium` | `str` | Yes | |
| `no_data_value` | `float` | Yes | |
| `aggregation_statistic` | `str` | Yes | |
| `time_aggregation_interval` | `float` | Yes | |
| `time_aggregation_interval_unit` | `str` | Yes | `"seconds"`, `"minutes"`, `"hours"`, `"days"` |
| `intended_time_spacing` | `float \| None` | Yes | |
| `intended_time_spacing_unit` | `str \| None` | Yes | `"seconds"`, `"minutes"`, `"hours"`, `"days"` |
| `status` | `str \| None` | Yes | |
| `result_type` | `str` | Yes | |
| `value_count` | `int \| None` | Yes | |
| `phenomenon_begin_time` | `datetime \| None` | Yes | |
| `phenomenon_end_time` | `datetime \| None` | Yes | |
| `result_begin_time` | `datetime \| None` | Yes | |
| `result_end_time` | `datetime \| None` | Yes | |
| `is_private` | `bool` | Yes | |
| `is_visible` | `bool` | Yes | |
| `thing_id` | `UUID` | Yes | |
| `sensor_id` | `UUID` | Yes | |
| `observed_property_id` | `UUID` | Yes | |
| `processing_level_id` | `UUID` | Yes | |
| `unit_id` | `UUID` | Yes | |
| `workspace_id` | `UUID` | No | |
| `tags` | `Dict[str, str]` | No | Use tag methods to modify |
| `file_attachments` | `Dict[str, dict]` | No | Use attachment methods to modify |
| `workspace` | `Workspace` | No | Computed |
| `thing` | `Thing` | No | Computed; also settable via assignment |
| `sensor` | `Sensor` | No | Computed; also settable via assignment |
| `observed_property` | `ObservedProperty` | No | Computed; also settable via assignment |
| `unit` | `Unit` | No | Computed; also settable via assignment |
| `processing_level` | `ProcessingLevel` | No | Computed; also settable via assignment |

The computed relationship properties (`thing`, `sensor`, etc.) can be assigned directly — assigning a new value updates the corresponding `_id` field and clears the cache:

```python
datastream.sensor = new_sensor  # updates sensor_id and clears cached sensor
datastream.save()
```

### Service methods

```python
hs_api.datastreams.list(workspace=None, thing=None) -> HydroServerCollection[Datastream]
hs_api.datastreams.get(uid) -> Datastream
hs_api.datastreams.create(name, description, thing, sensor, observed_property, processing_level,
                          unit, observation_type, result_type, sampled_medium, no_data_value,
                          aggregation_statistic, time_aggregation_interval,
                          time_aggregation_interval_unit, intended_time_spacing=None,
                          intended_time_spacing_unit=None, status=None, value_count=None,
                          phenomenon_begin_time=None, phenomenon_end_time=None,
                          result_begin_time=None, result_end_time=None,
                          is_private=False, is_visible=True, uid=None) -> Datastream
```

### Observation methods

```python
datastream.get_observations(
    phenomenon_time_min=None,
    phenomenon_time_max=None,
    result_qualifier_code=None,
    page=1,
    page_size=100000,
    order_by=None,
    fetch_all=False,
) -> ObservationCollection
```

Returns an `ObservationCollection` with a `dataframe` property containing a pandas DataFrame with `phenomenon_time` (timezone-aware datetime) and `result` (float) columns.

```python
datastream.load_observations(observations, mode='insert') -> None
```

`observations` must be a pandas DataFrame with `phenomenon_time` and `result` columns. `phenomenon_time` must be timezone-aware. `mode` is `"insert"` (skip existing timestamps) or `"replace"` (overwrite all observations in the datastream).

To load observations with result qualifiers, include a `result_qualifier_codes` column containing a list of qualifier code strings per row:

```python
df = pd.DataFrame({
    'phenomenon_time': times,
    'result': values,
    'result_qualifier_codes': [['PF'], [], ['ICE'], ...]
})
datastream.load_observations(df)
```

```python
datastream.delete_observations(phenomenon_time_start=None, phenomenon_time_end=None) -> None
```

Deletes observations within the given time range. If both parameters are omitted, all observations are deleted.

### Tag and file attachment methods

Same as Things — `add_tag`, `update_tag`, `delete_tag`, `add_file_attachment`, `delete_file_attachment`.

---

## ETL

### Data Connections

**Property:** `hs_api.dataconnections`

#### DataConnection properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `description` | `str \| None` | Yes | |
| `source_url` | `str` | Yes | URL template; use `{variable_name}` for placeholder substitution |
| `timezone_type` | `str \| None` | Yes | `"offset"` or `"iana"` |
| `timezone` | `str \| None` | Yes | e.g. `"+0000"` or `"America/Denver"` |
| `auth_header_name` | `str \| None` | Yes | |
| `auth_header_value` | `str \| None` | Yes | |
| `payload` | `CSVPayload \| JSONPayload` | No | See below |
| `placeholder_variables` | `List[PlaceholderVariable]` | No | See below |
| `notification` | `Notification \| None` | No | |
| `workspace_id` | `UUID` | No | |
| `workspace_name` | `str` | No | |
| `task_count` | `int` | No | Number of ETL tasks using this connection |
| `task_attention_count` | `int` | No | Tasks with a recent failure or overdue schedule |

**CSVPayload fields:** `payload_type` (`"CSV"`), `timestamp_key`, `timestamp_format`, `header_row`, `data_start_row`, `delimiter`

**JSONPayload fields:** `payload_type` (`"JSON"`), `timestamp_key`, `timestamp_format`, `jmespath`

**PlaceholderVariable fields:**

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Variable name as it appears in `{braces}` in `source_url` |
| `variable_type` | `str` | `"per_task"`, `"run_time"`, or `"latest_observation_timestamp"` |
| `timestamp_format` | `str \| None` | Custom strftime format; `None` uses ISO 8601 |

#### Service methods

```python
hs_api.dataconnections.list(workspace=None, payload_type=None) -> HydroServerCollection[DataConnection]
hs_api.dataconnections.get(uid) -> DataConnection
hs_api.dataconnections.create(
    name, workspace, source_url, payload_type, timestamp_key,
    description=None, timestamp_format=None, timezone_type=None, timezone=None,
    auth_header_name=None, auth_header_value=None,
    header_row=None, data_start_row=None, delimiter=None, jmespath=None,
    placeholder_variables=None, notification=None, uid=None
) -> DataConnection
hs_api.dataconnections.update(uid, name, source_url, payload_type, timestamp_key, ...) -> DataConnection
```

---

### ETL Tasks

**Property:** `hs_api.etltasks`

#### EtlTask properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `description` | `str \| None` | Yes | |
| `task_variables` | `Dict[str, Any]` | Yes | Values for `per_task` placeholder variables |
| `data_connection_id` | `UUID` | No | |
| `enabled` | `bool \| None` | Yes | |
| `start_time` | `datetime \| None` | Yes | |
| `crontab` | `str \| None` | Yes | |
| `interval` | `int \| None` | Yes | |
| `interval_period` | `str \| None` | Yes | `"minutes"`, `"hours"`, `"days"` |
| `next_run_at` | `datetime \| None` | No | |
| `latest_run` | `TaskRun \| None` | No | |
| `mappings` | `List[EtlMapping]` | Yes | |
| `data_connection` | `DataConnection` | No | Computed |

**EtlMapping fields:** `source_identifier` (`str`), `target_datastream` (`DatastreamSummary` with `id` and `name`)

#### Service methods

```python
hs_api.etltasks.list(
    workspace=None, data_connection=None, latest_run_status=None,
    latest_run_started_at_min=None, latest_run_started_at_max=None,
    latest_run_finished_at_min=None, latest_run_finished_at_max=None,
) -> HydroServerCollection[EtlTask]
hs_api.etltasks.get(uid) -> EtlTask
hs_api.etltasks.create(
    name, data_connection, description=None, task_variables=None,
    mappings=None, crontab=None, interval=None, interval_period=None,
    start_time=None, enabled=True, uid=None
) -> EtlTask
```

Mappings are a list of dicts with `source_identifier` and `target_datastream_id` keys.

#### Run methods

| Method | Returns | Description |
|---|---|---|
| `trigger()` | `TaskRun` | Dispatch an immediate run |
| `list_runs(status=None, started_at_min=None, started_at_max=None, finished_at_min=None, finished_at_max=None, page=1, page_size=100, order_by=None)` | `List[TaskRun]` | Fetch run history |
| `get_run(run_id)` | `TaskRun` | Fetch a single run by ID |

---

## Data Products

### Rating Curves

**Property:** `hs_api.ratingcurves`

#### RatingCurve properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `description` | `str \| None` | Yes | |
| `fitting_method` | `str` | Yes | `"linear"` or `"power_law"` |
| `thing_id` | `UUID` | No | |
| `thing_name` | `str` | No | |
| `points` | `List[Tuple[float, float]]` | Yes | List of `(input, output)` coordinate pairs |

#### Service methods

```python
hs_api.ratingcurves.list(workspace=None, thing=None) -> HydroServerCollection[RatingCurve]
hs_api.ratingcurves.get(uid) -> RatingCurve
hs_api.ratingcurves.create(name, thing, fitting_method, description=None, points=None, uid=None) -> RatingCurve
```

---

### Data Product Tasks

**Property:** `hs_api.dataproducttasks`

#### DataProductTask properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `description` | `str \| None` | Yes | |
| `thing_id` | `UUID` | No | |
| `thing_name` | `str` | No | |
| `enabled` | `bool \| None` | Yes | |
| `start_time` | `datetime \| None` | Yes | |
| `crontab` | `str \| None` | Yes | |
| `interval` | `int \| None` | Yes | |
| `interval_period` | `str \| None` | Yes | `"minutes"`, `"hours"`, `"days"` |
| `next_run_at` | `datetime \| None` | No | |
| `latest_run` | `TaskRun \| None` | No | |
| `rating_curve_transformations` | `List[RatingCurveTransformation]` | No | Manage via `hs_api.dataproducttransformations` |
| `expression_transformations` | `List[ExpressionTransformation]` | No | Manage via `hs_api.dataproducttransformations` |
| `composite_expression_transformations` | `List[CompositeExpressionTransformation]` | No | Manage via `hs_api.dataproducttransformations` |
| `aggregation_transformations` | `List[AggregationTransformation]` | No | Manage via `hs_api.dataproducttransformations` |

#### Service methods

```python
hs_api.dataproducttasks.list(
    workspace=None, thing=None, latest_run_status=None, transformation_type=None,
    output_datastream=None, input_datastream=None, rating_curve=None,
) -> HydroServerCollection[DataProductTask]
hs_api.dataproducttasks.get(uid) -> DataProductTask
hs_api.dataproducttasks.create(
    name, thing, description=None, crontab=None, interval=None,
    interval_period=None, start_time=None, enabled=True, uid=None
) -> DataProductTask
```

#### Run methods

Same as ETL Tasks: `trigger()`, `list_runs(...)`, `get_run(run_id)`.

---

### Data Product Transformations

**Property:** `hs_api.dataproducttransformations`

Transformations are always scoped to a specific data product task via `task_id`. All four types share a consistent set of CRUD methods.

#### Rating Curve Transformations

| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | |
| `output_datastream` | `DatastreamSummary` | `id` and `name` |
| `input_datastream` | `DatastreamSummary` | `id` and `name` |
| `rating_curve` | `RatingCurveSummary` | `id`, `name`, and `fitting_method` |

```python
hs_api.dataproducttransformations.list_rating_curve(task_id, output_datastream=None, input_datastream=None)
hs_api.dataproducttransformations.get_rating_curve(task_id, uid)
hs_api.dataproducttransformations.create_rating_curve(task_id, output_datastream, input_datastream, rating_curve, uid=None)
hs_api.dataproducttransformations.update_rating_curve(task_id, uid, input_datastream, rating_curve)
hs_api.dataproducttransformations.delete_rating_curve(task_id, uid)
```

#### Expression Transformations

| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | |
| `output_datastream` | `DatastreamSummary` | |
| `input_datastream` | `DatastreamSummary` | |
| `formula` | `str` | Python expression evaluated per observation |
| `variable_name` | `str \| None` | Name of the variable representing the input value in the formula |

```python
hs_api.dataproducttransformations.list_expression(task_id, output_datastream=None, input_datastream=None)
hs_api.dataproducttransformations.get_expression(task_id, uid)
hs_api.dataproducttransformations.create_expression(task_id, output_datastream, input_datastream, formula, variable_name=None, uid=None)
hs_api.dataproducttransformations.update_expression(task_id, uid, input_datastream, formula, variable_name=None)
hs_api.dataproducttransformations.delete_expression(task_id, uid)
```

#### Composite Expression Transformations

Like expression transformations, but combine multiple input datastreams. Each input datastream is assigned a variable name used in the formula.

| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | |
| `output_datastream` | `DatastreamSummary` | |
| `input_datastreams` | `List[TransformationInput]` | Each has `datastream` (`id`, `name`) and `variable_name` |
| `formula` | `str` | |
| `output_interval` | `int` | |
| `output_interval_units` | `str` | `"minutes"`, `"hours"`, `"days"`, `"weeks"`, `"months"` |
| `max_gap_interval` | `int \| None` | Max gap in input data before output is suppressed |
| `max_gap_interval_units` | `str \| None` | |

```python
hs_api.dataproducttransformations.list_composite_expression(task_id, output_datastream=None, input_datastream=None)
hs_api.dataproducttransformations.get_composite_expression(task_id, uid)
hs_api.dataproducttransformations.create_composite_expression(
    task_id, output_datastream, input_datastreams, formula,
    output_interval, output_interval_units,
    max_gap_interval=None, max_gap_interval_units=None, uid=None
)
hs_api.dataproducttransformations.update_composite_expression(
    task_id, uid, input_datastreams, formula,
    output_interval, output_interval_units,
    max_gap_interval=None, max_gap_interval_units=None
)
hs_api.dataproducttransformations.delete_composite_expression(task_id, uid)
```

`input_datastreams` is a list of dicts with `datastream_id` and optionally `variable_name`.

#### Aggregation Transformations

| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | |
| `output_datastream` | `DatastreamSummary` | |
| `input_datastream` | `DatastreamSummary` | |
| `aggregation_method` | `str` | `"mean"`, `"sum"`, `"min"`, `"max"`, `"first"`, `"last"` |
| `output_interval` | `int` | |
| `output_interval_units` | `str` | `"minutes"`, `"hours"`, `"days"`, `"weeks"`, `"months"` |
| `timezone_type` | `str \| None` | `"utc"`, `"offset"`, or `"iana"` |
| `timezone` | `str \| None` | Used to align interval boundaries (e.g. `"America/Denver"` for daily values in local time) |
| `min_values` | `int \| None` | Minimum number of input observations required to produce an output |

```python
hs_api.dataproducttransformations.list_aggregation(task_id, output_datastream=None, input_datastream=None)
hs_api.dataproducttransformations.get_aggregation(task_id, uid)
hs_api.dataproducttransformations.create_aggregation(
    task_id, output_datastream, input_datastream, aggregation_method,
    output_interval, output_interval_units,
    timezone_type=None, timezone=None, min_values=None, uid=None
)
hs_api.dataproducttransformations.update_aggregation(
    task_id, uid, input_datastream, aggregation_method,
    output_interval, output_interval_units,
    timezone_type=None, timezone=None, min_values=None
)
hs_api.dataproducttransformations.delete_aggregation(task_id, uid)
```

---

## Monitoring

### Monitoring Tasks

**Property:** `hs_api.monitoringtasks`

#### MonitoringTask properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `description` | `str \| None` | Yes | |
| `thing_id` | `UUID` | No | |
| `thing_name` | `str` | No | |
| `recipients` | `List[str]` | Yes | Email addresses to alert |
| `enabled` | `bool \| None` | Yes | |
| `start_time` | `datetime \| None` | Yes | |
| `crontab` | `str \| None` | Yes | |
| `interval` | `int \| None` | Yes | |
| `interval_period` | `str \| None` | Yes | `"minutes"`, `"hours"`, `"days"` |
| `next_run_at` | `datetime \| None` | No | |
| `latest_run` | `TaskRun \| None` | No | |
| `monitored_datastreams` | `List[MonitoredDatastream]` | No | Inline summary; manage rules via `hs_api.monitoringrules` |
| `rules` | `List[MonitoringRule]` | No | Computed; full rule objects for this task |

**MonitoredDatastream fields:** `datastream_id`, `datastream_name`, `rules` (list of inline rule summaries with `id`, `rule_type`, `last_checked_at`, `min_value`, `max_value`, `window_interval`, `window_interval_units`)

#### Service methods

```python
hs_api.monitoringtasks.list(
    workspace=None, thing=None, latest_run_status=None,
    datastream=None, rule_type=None,
) -> HydroServerCollection[MonitoringTask]
hs_api.monitoringtasks.get(uid) -> MonitoringTask
hs_api.monitoringtasks.create(
    name, thing, description=None, recipients=None,
    crontab=None, interval=None, interval_period=None,
    start_time=None, enabled=True, uid=None
) -> MonitoringTask
```

#### Run methods

Same as ETL Tasks: `trigger()`, `list_runs(...)`, `get_run(run_id)`.

---

### Monitoring Rules

**Property:** `hs_api.monitoringrules`

Rules are always scoped to a monitoring task via `task_id`.

#### MonitoringRule properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `task_id` | `UUID` | No | |
| `datastream_id` | `UUID` | No | |
| `datastream_name` | `str` | No | |
| `rule_type` | `str` | No | `"range"`, `"rate_of_change"`, `"persistence"`, or `"missing_data"` |
| `last_checked_at` | `datetime \| None` | No | |
| `min_value` | `float \| None` | Yes | Used by `range` and `rate_of_change` |
| `max_value` | `float \| None` | Yes | Used by `range` and `rate_of_change` |
| `window_interval` | `int \| None` | Yes | Used by `persistence` and `missing_data` |
| `window_interval_units` | `str \| None` | Yes | `"minutes"`, `"hours"`, `"days"` |

**Rule types:**

| Rule type | Alert condition | Parameters used |
|---|---|---|
| `range` | Latest value outside `[min_value, max_value]` | `min_value`, `max_value` |
| `rate_of_change` | Change between consecutive values outside `[min_value, max_value]` | `min_value`, `max_value` |
| `persistence` | Value unchanged for longer than `window_interval` | `window_interval`, `window_interval_units` |
| `missing_data` | No new observations within `window_interval` | `window_interval`, `window_interval_units` |

#### Service methods

```python
hs_api.monitoringrules.list(task_id, datastream=None, rule_type=None) -> HydroServerCollection[MonitoringRule]
hs_api.monitoringrules.get(task_id, uid) -> MonitoringRule
hs_api.monitoringrules.create(
    task_id, datastream, rule_type,
    min_value=None, max_value=None,
    window_interval=None, window_interval_units=None,
    uid=None
) -> MonitoringRule
```