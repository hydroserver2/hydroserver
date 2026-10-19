# Python Client Reference — hydroserverpy

`hydroserverpy` is HydroServer's official Python client library. This page is a reference for the classes, properties, and methods it exposes. If you're new to the library, start with the [Getting Started with hydroserverpy](/user-guides/tutorials/getting-started-with-hydroserverpy/) tutorial series.

---

## Installation

hydroserverpy 2.x works with HydroServer 2.x and requires Python 3.9 or higher.

```bash
pip install "hydroserverpy>=2.0,<3"
```

---

## Connection

```python
from hydroserverpy import HydroServer

# Email/password authentication
hs_api = HydroServer(host, email=email, password=password)

# API key authentication (a service account key)
hs_api = HydroServer(host, apikey=apikey)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `host` | `str` | — | Base URL of your HydroServer instance |
| `base_route` | `str` | `"/api/ogc"` | API path prefix; only change this for non-standard deployments |
| `email` | `str` | `None` | Account email; must be given together with `password` |
| `password` | `str` | `None` | Account password |
| `apikey` | `str` | `None` | Service account API key (alternative to email/password) |

API keys belong to [service accounts](#service-accounts). They can read and write data the service account has access to, but cannot manage workspace access (collaborators, service accounts, ownership) — use email/password for those operations.

`hs_api.request(method, path, **kwargs)` sends a raw request through the authenticated session, for endpoints the client doesn't wrap.

---

## Common Patterns

### HydroServerCollection

`list()` methods return a `HydroServerCollection` rather than a plain list.

| Property | Type | Description |
|---|---|---|
| `items` | `List[T]` | The resources on the current page |
| `offset` | `int \| None` | Offset of the current page |
| `limit` | `int \| None` | Page size of the current page |
| `total_count` | `int \| None` | Total number of matching resources |
| `filters` | `dict \| None` | Filters used for this query (reused by the paging methods) |
| `sortby` | `List[str] \| None` | Sort order used for this query |

| Method | Returns | Description |
|---|---|---|
| `next_page()` | `HydroServerCollection` | Fetch the next page |
| `previous_page()` | `HydroServerCollection \| None` | Fetch the previous page (`None` on the first page) |
| `fetch_all()` | `HydroServerCollection` | Fetch every remaining page and merge them into one collection |

### Common list() parameters

All `list()` methods accept these parameters in addition to any resource-specific filters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `offset` | `int` | server default (`0`) | Number of results to skip |
| `limit` | `int` | server default (`100`) | Results per page |
| `sortby` | `List[str]` | server default | Fields to sort by; prefix with `-` for descending, e.g. `["-name"]` |
| `fetch_all` | `bool` | `False` | If `True`, fetches and merges all pages automatically |

Filters that take a resource (for example `workspace=` or `monitoring_site=`) accept either the object or its UUID.

### Model methods

Resource objects share these methods inherited from `HydroServerBaseModel`:

| Method | Description |
|---|---|
| `save()` | Send modified **editable** fields back to HydroServer |
| `refresh()` | Re-fetch this resource's data from HydroServer |
| `delete()` | Delete this resource from HydroServer and set `uid` to `None` |

By default, `save()` sends only the editable fields you have changed since the object was loaded. A few models override this and send all of their fields on every save: `DataConnection`, `EtlTask`, and `RatingCurve` (noted in their sections below).

Properties marked **computed** in the tables below are lazy-loaded — they make an API call on first access and are then cached on the object.

### Service update() methods

Every service also has `update(uid, ...)` and `delete(uid)` methods. For most resources, any argument you leave out of `update()` is left unchanged on the server. The exceptions — methods that replace a value when you omit it — are called out in their sections: [`etltasks.update`](#etl-tasks), [`dataconnections.update`](#data-connections), [`ratingcurves.update`](#rating-curves), and the transformation `update_*` methods.

All service methods that take a `uid` accept a `UUID` or a string. `create()` methods also accept an optional `uid=` if you want to choose the new resource's ID yourself; otherwise the server assigns one.

### Schedules

ETL tasks, data product tasks, and monitoring tasks share the same schedule fields:

| Field | Type | Description |
|---|---|---|
| `enabled` | `bool \| None` | Whether the schedule is active |
| `crontab` | `str \| None` | Cron expression, e.g. `"0 6 * * *"`; use instead of `interval` |
| `interval` | `int \| None` | Repeat every `interval` × `interval_period` |
| `interval_period` | `str \| None` | `"minutes"`, `"hours"`, or `"days"` |
| `start_time` | `datetime \| None` | When the schedule starts |
| `next_run_at` | `datetime \| None` | Next scheduled run (read-only, set by the server) |

When updating a task, schedule fields you leave out keep their current values. Passing both `crontab=None` and `interval=None` removes the schedule.

### TaskRun

Returned by `trigger()`, `list_runs()`, and `get_run()` across ETL tasks, data product tasks, and monitoring tasks, and in each task's `latest_run`.

| Property | Type | Description |
|---|---|---|
| `id` | `UUID` | Run identifier |
| `status` | `str` | `"PENDING"`, `"STARTED"`, `"SUCCESS"`, or `"FAILURE"` |
| `message` | `str \| None` | Human-readable status message |
| `result` | `dict \| None` | Detailed result payload |
| `started_at` | `datetime \| None` | When the run started |
| `finished_at` | `datetime \| None` | When the run finished |

A run stays `PENDING` until an orchestration worker picks it up; if it never leaves `PENDING`, check that your instance's workers are running.

### Error handling

Failed requests raise `requests.HTTPError`. For 4xx responses, the message includes HydroServer's explanation, and the original response is available on the exception:

```python
import requests

try:
    datastream.load_observations(df)
except requests.HTTPError as e:
    print(e)                       # "409 Client Error: Duplicate phenomenonTime found on this datastream."
    print(e.response.status_code)  # 409
```

| Status | Typical cause |
|---|---|
| `400` | Invalid input (the message says which field) |
| `401` | Missing or invalid credentials, or an API key used for an operation that requires email/password |
| `403` | Your account or service account lacks permission for this action |
| `404` | The resource doesn't exist, or you don't have permission to see it |
| `409` | Conflict with existing data, e.g. duplicate observation timestamps or a duplicate unique value |

The client retries a request once, with a fresh session, after a connection error or a `401`/`403` response.

---

## Workspaces

**Property:** `hs_api.workspaces`

### Workspace properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `is_private` | `bool` | Yes | |
| `owner_email` | `str` | No | Email of the workspace owner |
| `pending_transfer_to_email` | `str \| None` | No | Recipient of a pending ownership transfer |
| `collaborator_role_id` | `UUID \| None` | No | Your role in this workspace, if you're a collaborator |
| `collaborator_role` | `Role \| None` | No | Computed |
| `roles` | `List[Role]` | No | Computed; roles you can assign in this workspace, including system roles |
| `collaborators` | `List[Collaborator]` | No | Computed |
| `serviceaccounts` | `List[ServiceAccount]` | No | Computed |
| `monitoring_sites` | `List[MonitoringSite]` | No | Computed |
| `datastreams` | `List[Datastream]` | No | Computed |
| `observedproperties` | `List[ObservedProperty]` | No | Computed |
| `units` | `List[Unit]` | No | Computed |
| `processinglevels` | `List[ProcessingLevel]` | No | Computed |
| `resultqualifiers` | `List[ResultQualifier]` | No | Computed |
| `methods` | `List[Method]` | No | Computed |
| `dataconnections` | `List[DataConnection]` | No | Computed |
| `tasks` | `List[EtlTask]` | No | Computed; ETL tasks only |

### Service methods

```python
hs_api.workspaces.list(is_associated=..., is_private=...) -> HydroServerCollection[Workspace]
hs_api.workspaces.get(uid) -> Workspace
hs_api.workspaces.create(name, is_private, uid=None) -> Workspace
hs_api.workspaces.update(uid, name=..., is_private=...) -> Workspace
hs_api.workspaces.delete(uid) -> None
```

| Filter | Type | Description |
|---|---|---|
| `is_associated` | `bool` | Only return workspaces you own or collaborate on |
| `is_private` | `bool` | Filter by privacy setting |

### Collaborators

| Method | Description |
|---|---|
| `workspace.add_collaborator(email, role)` | Add a user (by email) or a `ServiceAccount` as a collaborator; `role` accepts a `Role` or role UUID |
| `workspace.edit_collaborator_role(email, role)` | Change an existing collaborator's role |
| `workspace.remove_collaborator(email)` | Remove a collaborator (user email or `ServiceAccount`) |

Use `workspace.roles` to find the role to assign. The same methods are available on the service as `hs_api.workspaces.add_collaborator(uid, email, role)` and so on, plus `list_collaborators(uid)`.

**Collaborator fields** (items in `workspace.collaborators`):

| Field | Type | Notes |
|---|---|---|
| `user_email` | `str \| None` | Set when the collaborator is a user |
| `service_account_email` | `str \| None` | Set when the collaborator is a service account |
| `email` | `str` | Whichever of the two is set |
| `is_service_account` | `bool` | |
| `role_id` | `UUID` | Editable |
| `workspace_id` | `UUID` | |
| `role` | `Role` | Computed; also settable via assignment |
| `workspace` | `Workspace` | Computed |

`collaborator.save()` applies a changed role; `collaborator.delete()` removes the collaborator from the workspace.

### Ownership transfer

| Method | Description |
|---|---|
| `workspace.transfer_ownership(email)` | Start an ownership transfer to another HydroServer user |
| `workspace.accept_ownership_transfer()` | Accept a pending transfer (called by the recipient) |
| `workspace.cancel_ownership_transfer()` | Cancel a pending transfer |

Each method refreshes the workspace afterward, so `owner_email` and `pending_transfer_to_email` reflect the new state.

### Roles

**Property:** `hs_api.roles`

Roles define what a collaborator can do in a workspace. System roles are available in every workspace; a workspace can also have its own roles. Roles are read-only through the API — calling `save()` or `delete()` on a `Role` raises `NotImplementedError`.

| Property | Type | Notes |
|---|---|---|
| `uid` | `UUID` | |
| `name` | `str` | |
| `description` | `str \| None` | |
| `workspace_id` | `UUID \| None` | `None` for system roles |
| `permissions` | `List[RolePermission]` | Each has `resource` (e.g. `"Datastream"`) and `action` (e.g. `"edit"`) |
| `workspace` | `Workspace \| None` | Computed |

```python
hs_api.roles.list(workspace=...) -> HydroServerCollection[Role]
hs_api.roles.get(uid) -> Role
```

`workspace` accepts a single workspace or a list; include `None` in the list to also match system roles. `workspace.roles` is shorthand for `hs_api.roles.list(workspace=[workspace, None], fetch_all=True).items`.

---

## Service Accounts

Service accounts let scripts and automated jobs access HydroServer with an API key instead of a user's email and password. A service account belongs to a workspace; give it access by assigning it a role (at creation, or later with `add_collaborator`).

Creating, updating, deleting, and regenerating service accounts requires email/password authentication.

### ServiceAccount properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `description` | `str \| None` | Yes | |
| `is_active` | `bool` | Yes | Inactive accounts can't authenticate |
| `key_expires_at` | `datetime \| None` | Yes | |
| `email` | `str` | No | Generated identifier used when adding the account as a collaborator |
| `workspace_id` | `UUID` | No | |
| `created_at` | `datetime` | No | |
| `last_used_at` | `datetime \| None` | No | |
| `workspace` | `Workspace` | No | Computed |

`ServiceAccount` objects support `save()`, `refresh()`, `delete()`, and `regenerate()`, which invalidates the old key and returns the new key string.

### Workspace methods

| Method | Description |
|---|---|
| `create_service_account(name, description=None, is_active=True, key_expires_at=None, role=None)` | Create a service account; returns `(ServiceAccount, key)`. If `role` is given, the account is also added as a collaborator with that role. |
| `update_service_account(service_account_id, name=..., description=..., is_active=..., key_expires_at=...)` | Update a service account |
| `delete_service_account(service_account_id)` | Delete a service account |
| `regenerate_service_account_key(service_account_id)` | Returns `(ServiceAccount, key)` with a new key |

The service exposes the same operations with the workspace UID as the first argument (`hs_api.workspaces.create_service_account(uid, name, ...)`), plus `list_service_accounts(uid)` and `get_service_account(uid, service_account_id)`.

The key is only returned when it is created or regenerated — store it securely. To use it:

```python
service_account, key = workspace.create_service_account(name="ETL job", role=editor_role)

hs_job = HydroServer(host, apikey=key)
```

---

## Monitoring Sites

**Property:** `hs_api.monitoring_sites`

### MonitoringSite properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `description` | `str` | Yes | |
| `code` | `str` | Yes | |
| `type` | `str` | Yes | |
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
| `tags` | `Dict[str, str]` | No | Use the tag methods to modify |
| `linked_resources` | `Dict[str, dict]` | No | Keyed by name; each has `id`, `link`, and `type`. Use the linked resource methods to modify |
| `workspace` | `Workspace` | No | Computed |
| `datastreams` | `List[Datastream]` | No | Computed |

### Service methods

```python
hs_api.monitoring_sites.list(workspace=..., bbox=..., admin_area_1=..., admin_area_2=...,
                             country=..., type=..., tag=..., is_private=...) -> HydroServerCollection[MonitoringSite]
hs_api.monitoring_sites.get(uid) -> MonitoringSite
hs_api.monitoring_sites.create(workspace, name, description, code, type,
                               is_private, latitude, longitude, elevation_m=None,
                               elevation_datum=None, admin_area_1=None, admin_area_2=None,
                               country=None, data_disclaimer=None, tags=None, uid=None) -> MonitoringSite
hs_api.monitoring_sites.update(uid, name=..., description=..., code=..., type=..., is_private=...,
                               latitude=..., longitude=..., elevation_m=..., elevation_datum=...,
                               admin_area_1=..., admin_area_2=..., country=...,
                               data_disclaimer=..., tags=...) -> MonitoringSite
hs_api.monitoring_sites.delete(uid) -> None
```

| Filter | Type | Description |
|---|---|---|
| `workspace` | `Workspace \| UUID \| str` | Filter by workspace |
| `bbox` | `tuple` | `(min_lon, min_lat, max_lon, max_lat)` bounding box |
| `admin_area_1` | `str` | Filter by state/province |
| `admin_area_2` | `str` | Filter by county/district |
| `country` | `str` | Filter by country code |
| `type` | `str` | Filter by site type |
| `tag` | `tuple` | `(key, value)` filter by tag |
| `is_private` | `bool` | Filter by privacy setting |

### Tags

| Method | Description |
|---|---|
| `site.set_tag(key, value)` | Add or update a tag |
| `site.delete_tag(key)` | Remove a tag |

`update(uid, tags={...})` merges the given tags into the existing ones; a value of `None` removes that key. Tags you don't mention are kept.

### Linked resources

| Method | Description |
|---|---|
| `site.add_linked_resource(name, type, file=None, url=None, description=None)` | Attach a file (`file` opened in binary mode) or a link (`url`) |
| `site.delete_linked_resource(name)` | Remove a linked resource by name |

The service also provides `get_linked_resources(uid, offset=..., limit=..., type=...)`, `get_linked_resource(uid, linked_resource_id)`, `update_linked_resource(uid, linked_resource_id, name=None, type=None, file=None, url=None, description=None)`, and `delete_linked_resource(uid, linked_resource_id)`.

---

## Metadata

Methods, observed properties, units, processing levels, and result qualifiers all follow the same shape: a small set of editable fields, a read-only `workspace_id`, and a computed `workspace` property. They support the standard `save()`, `refresh()`, and `delete()` model methods.

### Methods

**Property:** `hs_api.methods`

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `description` | `str` | Yes | |
| `code` | `str \| None` | Yes | |
| `type` | `str` | Yes | |
| `sensor_model` | `str \| None` | Yes | |
| `sensor_model_manufacturer` | `str \| None` | Yes | |
| `sensor_model_definition` | `str \| None` | Yes | |
| `definition` | `str \| None` | Yes | |
| `workspace_id` | `UUID \| None` | No | |
| `workspace` | `Workspace \| None` | No | Computed |

```python
hs_api.methods.list(workspace=..., monitoring_site=..., datastream=..., type=...,
                    sensor_model=..., sensor_model_manufacturer=...) -> HydroServerCollection[Method]
hs_api.methods.get(uid) -> Method
hs_api.methods.create(name, description, type, code=None, definition=None,
                      sensor_model=None, sensor_model_manufacturer=None,
                      sensor_model_definition=None, workspace=None, uid=None) -> Method
hs_api.methods.update(uid, name=..., description=..., type=..., code=..., definition=...,
                      sensor_model=..., sensor_model_manufacturer=...,
                      sensor_model_definition=...) -> Method
```

### Observed Properties

**Property:** `hs_api.observedproperties`

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `definition` | `str \| None` | Yes | |
| `description` | `str` | Yes | |
| `type` | `str` | Yes | |
| `code` | `str \| None` | Yes | |
| `workspace_id` | `UUID \| None` | No | |
| `workspace` | `Workspace \| None` | No | Computed |

```python
hs_api.observedproperties.list(workspace=..., monitoring_site=..., datastream=..., type=...) -> HydroServerCollection[ObservedProperty]
hs_api.observedproperties.get(uid) -> ObservedProperty
hs_api.observedproperties.create(name, description, type, code=None, definition=None,
                                 workspace=None, uid=None) -> ObservedProperty
hs_api.observedproperties.update(uid, name=..., description=..., type=..., code=..., definition=...) -> ObservedProperty
```

### Units

**Property:** `hs_api.units`

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `symbol` | `str` | Yes | |
| `definition` | `str \| None` | Yes | |
| `type` | `str` | Yes | |
| `workspace_id` | `UUID \| None` | No | |
| `workspace` | `Workspace \| None` | No | Computed |

```python
hs_api.units.list(workspace=..., monitoring_site=..., datastream=..., type=...) -> HydroServerCollection[Unit]
hs_api.units.get(uid) -> Unit
hs_api.units.create(name, symbol, type, definition=None, workspace=None, uid=None) -> Unit
hs_api.units.update(uid, name=..., symbol=..., type=..., definition=...) -> Unit
```

### Processing Levels

**Property:** `hs_api.processinglevels`

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `code` | `str \| None` | Yes | |
| `name` | `str` | Yes | |
| `description` | `str` | Yes | |
| `definition` | `str \| None` | Yes | |
| `workspace_id` | `UUID \| None` | No | |
| `workspace` | `Workspace \| None` | No | Computed |

```python
hs_api.processinglevels.list(workspace=..., monitoring_site=..., datastream=...) -> HydroServerCollection[ProcessingLevel]
hs_api.processinglevels.get(uid) -> ProcessingLevel
hs_api.processinglevels.create(name, description, *, code=None, definition=None, workspace=None, uid=None) -> ProcessingLevel
hs_api.processinglevels.update(uid, code=..., name=..., description=..., definition=...) -> ProcessingLevel
```

Processing-level creation accepts `name` and `description` by position or by keyword. Optional arguments must be named, for example `create("Raw", "Unprocessed data", code="0")`. The old `create("0", "Raw", "Unprocessed data")` call raises Python's built-in `TypeError`; move the old first argument to `code=`. Processing-level updates retain their existing argument order: `update(uid, code, name, description, definition)`.

### Result Qualifiers

**Property:** `hs_api.resultqualifiers`

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `description` | `str \| None` | Yes | |
| `workspace_id` | `UUID \| None` | No | |
| `workspace` | `Workspace \| None` | No | Computed |

```python
hs_api.resultqualifiers.list(workspace=...) -> HydroServerCollection[ResultQualifier]
hs_api.resultqualifiers.get(uid) -> ResultQualifier
hs_api.resultqualifiers.create(name, description=None, workspace=None, uid=None) -> ResultQualifier
hs_api.resultqualifiers.update(uid, name=..., description=...) -> ResultQualifier
```

Result-qualifier creation accepts `name` and `description` by position or by keyword; `description` is optional.

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
| `value_count` | `int \| None` | No | Maintained from observations |
| `phenomenon_begin_time` | `datetime \| None` | No | Maintained from observations |
| `phenomenon_end_time` | `datetime \| None` | No | Maintained from observations |
| `result_begin_time` | `datetime \| None` | No | Maintained from observations |
| `result_end_time` | `datetime \| None` | No | Maintained from observations |
| `is_private` | `bool` | Yes | |
| `is_visible` | `bool` | Yes | |
| `monitoring_site_id` | `UUID` | Yes | |
| `method_id` | `UUID` | Yes | |
| `observed_property_id` | `UUID` | Yes | |
| `processing_level_id` | `UUID` | Yes | |
| `unit_id` | `UUID` | Yes | |
| `workspace_id` | `UUID` | No | |
| `tags` | `Dict[str, str]` | No | Use the tag methods to modify |
| `linked_resources` | `Dict[str, dict]` | No | Use the linked resource methods to modify |
| `workspace` | `Workspace` | No | Computed |
| `monitoring_site` | `MonitoringSite` | No | Computed; also settable via assignment |
| `method` | `Method` | No | Computed; also settable via assignment |
| `observed_property` | `ObservedProperty` | No | Computed; also settable via assignment |
| `unit` | `Unit` | No | Computed; also settable via assignment |
| `processing_level` | `ProcessingLevel` | No | Computed; also settable via assignment |

The computed relationship properties (`monitoring_site`, `method`, etc.) can be assigned directly — assigning a new value updates the corresponding `_id` field and clears the cache:

```python
datastream.method = new_method  # updates method_id and clears cached method
datastream.save()
```

### Service methods

```python
hs_api.datastreams.list(workspace=..., monitoring_site=..., method=..., observed_property=...,
                        processing_level=..., unit=..., observation_type=..., sampled_medium=...,
                        status=..., result_type=..., tag=..., is_private=...,
                        value_count_min=..., value_count_max=...,
                        phenomenon_time_min=..., phenomenon_time_max=...) -> HydroServerCollection[Datastream]
hs_api.datastreams.get(uid) -> Datastream
hs_api.datastreams.create(name, description, monitoring_site, method, observed_property, processing_level,
                          unit, observation_type, result_type, sampled_medium, no_data_value,
                          aggregation_statistic, time_aggregation_interval,
                          time_aggregation_interval_unit, intended_time_spacing=None,
                          intended_time_spacing_unit=None, status=None,
                          is_private=False, is_visible=True, tags=None, uid=None) -> Datastream
hs_api.datastreams.update(uid, name=..., description=..., monitoring_site=..., method=...,
                          observed_property=..., processing_level=..., unit=..., ...) -> Datastream
hs_api.datastreams.delete(uid) -> None
```

`update()` accepts every editable field above. Relationships can be given as objects or UUIDs (`method=` or `method_id=`), and `tags=` merges the same way as for monitoring sites.

### Observation methods

```python
datastream.get_observations(
    phenomenon_time_min=...,
    phenomenon_time_max=...,
    result_qualifiers=...,
    offset=...,
    limit=100000,
    sortby=...,
    fetch_all=False,
) -> ObservationCollection
```

Returns an `ObservationCollection`. Its `dataframe` property is a pandas DataFrame with `phenomenon_time` (timezone-aware datetime), `result` (float), and `result_qualifiers` (list of qualifier names) columns. Like `HydroServerCollection`, it has `offset`, `limit`, and `total_count` properties and `next_page()`, `previous_page()`, and `fetch_all()` methods. Pass `result_qualifiers="PF"` to return only observations with that qualifier.

```python
datastream.load_observations(observations, mode='insert') -> None
```

`observations` must be a pandas DataFrame with `phenomenon_time` and `result` columns; `phenomenon_time` must be timezone-aware.

| `mode` | Behavior |
|---|---|
| `"insert"` (default) | Adds the observations. If any timestamp already exists in the datastream, the whole request is rejected with a `409` and nothing is loaded. |
| `"replace"` | Replaces the datastream's observations between the earliest and latest timestamp in your DataFrame with the ones you provide. Observations outside that range are untouched. |

To load observations with result qualifiers, include a `result_qualifiers` column containing a list of qualifier names per row. The names must match result qualifiers that exist in the datastream's workspace:

```python
df = pd.DataFrame({
    'phenomenon_time': times,
    'result': values,
    'result_qualifiers': [['PF'], [], ['ICE'], ...]
})
datastream.load_observations(df)
```

```python
datastream.delete_observations(phenomenon_time_start=None, phenomenon_time_end=None) -> None
```

Deletes observations within the given time range. If both parameters are omitted, all observations are deleted.

```python
datastream.sync_phenomenon_end_time() -> None
```

Reloads `phenomenon_end_time` and the datastream's other observation statistics, which HydroServer updates whenever observations are written.

### Tag and linked resource methods

Same as monitoring sites — `set_tag`, `delete_tag`, `add_linked_resource`, `delete_linked_resource` on the object, and `get_linked_resources`, `get_linked_resource`, `update_linked_resource`, `delete_linked_resource` on the service.

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
| `timezone` | `str \| None` | Yes | e.g. `"-0700"` or `"America/Denver"` |
| `auth_header_name` | `str \| None` | Yes | |
| `auth_header_value` | `str \| None` | Yes | |
| `payload` | `CSVPayload \| JSONPayload` | Yes | See below |
| `placeholder_variables` | `List[PlaceholderVariable]` | Yes | See below |
| `notification` | `Notification \| None` | Yes | See below |
| `workspace_id` | `UUID` | No | |
| `workspace` | `Workspace` | No | Computed |
| `task_count` | `int` | No | Number of ETL tasks using this connection |
| `task_attention_count` | `int` | No | Tasks with a recent failure or overdue schedule |

`DataConnection.save()` sends all of the connection's fields, including the full payload and placeholder variable list.

**CSVPayload fields:** `payload_type` (`"CSV"`), `timestamp_key`, `timestamp_format`, `header_row`, `data_start_row`, `delimiter`

**JSONPayload fields:** `payload_type` (`"JSON"`), `timestamp_key`, `timestamp_format`, `jmespath`

**PlaceholderVariable fields:**

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Variable name as it appears in `{braces}` in `source_url` |
| `variable_type` | `str` | `"per_task"`, `"run_time"`, `"latest_observation_timestamp"`, `"window_start"`, or `"window_end"` |
| `timestamp_format` | `str \| None` | Custom strftime format for timestamp variables; `None` uses ISO 8601 |

`per_task` values are supplied by each ETL task's `task_variables`. `run_time` is the time the task runs, and `latest_observation_timestamp` is the most recent observation already loaded (1970-01-01 for an empty datastream).

**Notification fields:** `recipient_emails` (`List[str]`) and `schedule` (a [schedule](#schedules), or `None`). On each scheduled notification, HydroServer emails the recipients a summary of the connection's ETL task runs since the previous one.

#### Service methods

```python
hs_api.dataconnections.list(workspace=..., payload_type=...) -> HydroServerCollection[DataConnection]
hs_api.dataconnections.get(uid) -> DataConnection
hs_api.dataconnections.create(
    name, workspace, source_url, timestamp_key, payload_type,
    description=None, timestamp_format=None, timezone_type=None, timezone=None,
    auth_header_name=None, auth_header_value=None,
    header_row=None, data_start_row=None, delimiter=None, jmespath=None,
    placeholder_variables=None, notification=None, uid=None
) -> DataConnection
hs_api.dataconnections.update(
    uid, name, source_url, timestamp_key, payload_type,
    description=..., timestamp_format=..., timezone_type=..., timezone=...,
    auth_header_name=..., auth_header_value=...,
    header_row=None, data_start_row=None, delimiter=None, jmespath=None,
    placeholder_variables=None, notification=...
) -> DataConnection
hs_api.dataconnections.delete(uid) -> None
```

`placeholder_variables` is a list of dicts with `name`, `variable_type`, and optionally `timestamp_format`.

::: warning
`dataconnections.update()` replaces the payload settings and the placeholder variable list with what you pass. If you leave out `placeholder_variables`, the connection's placeholder variables are **removed**; pass the full list on every update. Updating the object with `save()` avoids this, since it sends the current values.
:::

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
| `workspace_id` | `UUID` | No | |
| `enabled`, `crontab`, `interval`, `interval_period`, `start_time` | | Yes | See [Schedules](#schedules) |
| `next_run_at` | `datetime \| None` | No | |
| `latest_run` | `TaskRun \| None` | No | |
| `mapping_count` | `int` | No | Number of mappings on this task |
| `mappings` | `List[EtlMapping]` | No | Computed; manage with `hs_api.etlmappings` |
| `data_connection` | `DataConnection` | No | Computed |

`EtlTask.save()` sends all of the task's editable fields, including the full `task_variables` dict.

#### Service methods

```python
hs_api.etltasks.list(
    workspace=..., data_connection=..., latest_run_status=...,
    latest_run_started_at_min=..., latest_run_started_at_max=...,
    latest_run_finished_at_min=..., latest_run_finished_at_max=...,
) -> HydroServerCollection[EtlTask]
hs_api.etltasks.get(uid) -> EtlTask
hs_api.etltasks.create(
    name, data_connection, description=None, task_variables=None,
    crontab=None, interval=None, interval_period=None,
    start_time=None, enabled=True, uid=None
) -> EtlTask
hs_api.etltasks.update(
    uid, name, description=..., task_variables=None,
    crontab=..., interval=..., interval_period=..., start_time=..., enabled=...
) -> EtlTask
hs_api.etltasks.delete(uid) -> None
```

::: warning
`etltasks.update()` requires `name` and replaces `task_variables` with what you pass. If you leave out `task_variables`, the task's variables are **cleared**; pass the full dict on every update, or change the object and call `save()`.
:::

#### Run methods

| Method | Returns | Description |
|---|---|---|
| `trigger()` | `TaskRun` | Dispatch an immediate run |
| `list_runs(status=..., started_at_min=..., started_at_max=..., finished_at_min=..., finished_at_max=..., offset=..., limit=..., sortby=...)` | `List[TaskRun]` | Fetch run history, newest first |
| `get_run(run_id)` | `TaskRun` | Fetch a single run by ID |

The service has the same methods with the task UID as the first argument, e.g. `hs_api.etltasks.trigger(uid)`.

---

### ETL Mappings

**Property:** `hs_api.etlmappings`

A mapping tells an ETL task which field (or column) in the extracted data to load into which datastream. A task needs at least one mapping to load anything.

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `task_id` | `UUID` | No | |
| `source_identifier` | `str` | Yes | Column name (CSV) or record field (JSON) holding the values |
| `target_datastream_id` | `UUID` | Yes | Datastream the values are loaded into |

```python
hs_api.etlmappings.list(etl_task=..., workspace=..., source_identifier=...) -> HydroServerCollection[EtlMapping]
hs_api.etlmappings.get(uid) -> EtlMapping
hs_api.etlmappings.create(task_id, source_identifier, target_datastream, uid=None) -> EtlMapping
hs_api.etlmappings.update(uid, source_identifier=..., target_datastream=...) -> EtlMapping
hs_api.etlmappings.delete(uid) -> None
```

```python
task = hs_api.etltasks.create(name="Gage height", data_connection=connection,
                              task_variables={"site_code": "10109000"})
hs_api.etlmappings.create(task_id=task.uid, source_identifier="value",
                          target_datastream=datastream)
```

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
| `points` | `List[Tuple[float, float]]` | Yes | List of `(input, output)` pairs |
| `monitoring_site_id` | `UUID` | No | |
| `monitoring_site` | `MonitoringSite` | No | Computed |

`RatingCurve.save()` sends all of the curve's editable fields.

#### Service methods

```python
hs_api.ratingcurves.list(workspace=..., monitoring_site=...) -> HydroServerCollection[RatingCurve]
hs_api.ratingcurves.get(uid) -> RatingCurve
hs_api.ratingcurves.create(name, monitoring_site, fitting_method, description=None, points=None, uid=None) -> RatingCurve
hs_api.ratingcurves.update(uid, name, fitting_method, points, description=...) -> RatingCurve
hs_api.ratingcurves.delete(uid) -> None
```

`update()` requires `name`, `fitting_method`, and the full `points` list, which replaces the existing points.

---

### Data Product Tasks

**Property:** `hs_api.dataproducttasks`

#### DataProductTask properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `name` | `str` | Yes | |
| `description` | `str \| None` | Yes | |
| `monitoring_site_id` | `UUID` | No | |
| `workspace_id` | `UUID` | No | |
| `enabled`, `crontab`, `interval`, `interval_period`, `start_time` | | Yes | See [Schedules](#schedules) |
| `next_run_at` | `datetime \| None` | No | |
| `latest_run` | `TaskRun \| None` | No | |
| `transformation_types` | `List[str]` | No | Types of transformations attached to the task |
| `rating_curve_transformations` | `List[RatingCurveTransformation]` | No | Computed; manage via `hs_api.dataproducttransformations` |
| `derivation_transformations` | `List[DerivationTransformation]` | No | Computed; manage via `hs_api.dataproducttransformations` |
| `aggregation_transformations` | `List[AggregationTransformation]` | No | Computed; manage via `hs_api.dataproducttransformations` |

#### Service methods

```python
hs_api.dataproducttasks.list(
    workspace=..., monitoring_site=..., latest_run_status=..., transformation_type=...,
    output_datastream=..., input_datastream=..., rating_curve=...,
) -> HydroServerCollection[DataProductTask]
hs_api.dataproducttasks.get(uid) -> DataProductTask
hs_api.dataproducttasks.create(
    name, monitoring_site, description=None, crontab=None, interval=None,
    interval_period=None, start_time=None, enabled=True, uid=None
) -> DataProductTask
hs_api.dataproducttasks.update(
    uid, name=..., description=..., crontab=..., interval=..., interval_period=...,
    start_time=..., enabled=...
) -> DataProductTask
hs_api.dataproducttasks.delete(uid) -> None
```

#### Run methods

Same as ETL Tasks: `trigger()`, `list_runs(...)`, `get_run(run_id)`.

---

### Data Product Transformations

**Property:** `hs_api.dataproducttransformations`

Transformations are attached to a data product task when created (`task_id`), and identified by their own `uid` after that. All three types share these fields:

| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | |
| `task_id` | `UUID` | |
| `output_datastream_id` | `UUID` | |
| `input_datastreams` | `List[TransformationInput]` | Each has `datastream_id` and `variable_name` |
| `transformation_type` | `str` | `"rating_curve"`, `"derivation"`, or `"aggregation"` |

The `list_*` methods take optional filters: `task_id`, `workspace_id`, `output_datastream`, and `input_datastream`.

#### Rating Curve Transformations

Converts each input value using a [rating curve](#rating-curves).

| Field | Type | Description |
|---|---|---|
| `rating_curve_id` | `UUID` | |
| `input_datastream_id` | `UUID` | Convenience property for the single input |

```python
hs_api.dataproducttransformations.list_rating_curve(task_id=None, workspace_id=None, output_datastream=None, input_datastream=None)
hs_api.dataproducttransformations.get_rating_curve(uid)
hs_api.dataproducttransformations.create_rating_curve(task_id, output_datastream, input_datastream, rating_curve, uid=None)
hs_api.dataproducttransformations.update_rating_curve(uid, input_datastream, rating_curve)
hs_api.dataproducttransformations.delete_rating_curve(uid)
```

#### Derivation Transformations

Combines one or more input datastreams using a formula. Each input datastream is assigned a variable name used in the formula; with a single input, this is equivalent to applying the formula to each observation independently. Multiple inputs are matched by exact timestamp — if they stop lining up, a run stops there until the inputs are back in sync.

| Field | Type | Description |
|---|---|---|
| `formula` | `str` | Python expression referencing the input variable name(s) |
| `stop_on_no_data` | `bool` | If `True`, stop the run when an input holds its no-data value; if `False`, fill the output with its no-data value and continue |
| `stop_on_error` | `bool` | If `True`, stop the run when the formula produces a non-finite result; if `False`, fill the output with its no-data value and continue |

```python
hs_api.dataproducttransformations.list_derivation(task_id=None, workspace_id=None, output_datastream=None, input_datastream=None)
hs_api.dataproducttransformations.get_derivation(uid)
hs_api.dataproducttransformations.create_derivation(
    task_id, output_datastream, input_datastreams, formula,
    stop_on_no_data=True, stop_on_error=True, uid=None
)
hs_api.dataproducttransformations.update_derivation(
    uid, input_datastreams=..., formula=..., stop_on_no_data=..., stop_on_error=...
)
hs_api.dataproducttransformations.delete_derivation(uid)
```

`input_datastreams` is a list of dicts with `datastream_id` and `variable_name`, for example `[{'datastream_id': stage.uid, 'variable_name': 'x'}]`. On `update_derivation`, any argument you leave out is left unchanged.

#### Aggregation Transformations

| Field | Type | Description |
|---|---|---|
| `input_datastream_id` | `UUID` | Convenience property for the single input |
| `aggregation_method` | `str` | `"mean"`, `"sum"`, `"min"`, `"max"`, `"first"`, `"last"`, or `"time_weighted_mean"` |
| `output_interval` | `int` | |
| `output_interval_units` | `str` | `"minutes"`, `"hours"`, `"days"`, `"weeks"`, `"months"` |
| `timezone_type` | `str \| None` | `"utc"`, `"offset"`, or `"iana"` |
| `timezone` | `str \| None` | Used to align interval boundaries (e.g. `"America/Denver"` for daily values in local time) |
| `min_values` | `int \| None` | Minimum number of input observations required to produce an output |

```python
hs_api.dataproducttransformations.list_aggregation(task_id=None, workspace_id=None, output_datastream=None, input_datastream=None)
hs_api.dataproducttransformations.get_aggregation(uid)
hs_api.dataproducttransformations.create_aggregation(
    task_id, output_datastream, input_datastream, aggregation_method,
    output_interval, output_interval_units,
    timezone_type=None, timezone=None, min_values=None, uid=None
)
hs_api.dataproducttransformations.update_aggregation(
    uid, input_datastream, aggregation_method,
    output_interval, output_interval_units,
    timezone_type=None, timezone=None, min_values=None
)
hs_api.dataproducttransformations.delete_aggregation(uid)
```

`update_rating_curve` and `update_aggregation` replace the whole transformation: pass every field, since optional fields you leave out are reset to `None`.

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
| `monitoring_site_id` | `UUID` | No | |
| `workspace_id` | `UUID` | No | |
| `recipients` | `List[str]` | Yes | Email addresses to alert |
| `enabled`, `crontab`, `interval`, `interval_period`, `start_time` | | Yes | See [Schedules](#schedules) |
| `next_run_at` | `datetime \| None` | No | |
| `latest_run` | `TaskRun \| None` | No | |
| `rule_type_counts` | `Dict[str, int]` | No | Number of rules of each type, e.g. `{"range": 1, "missing_data": 1}` |
| `rules` | `List[MonitoringRule]` | No | Computed; full rule objects for this task |

#### Service methods

```python
hs_api.monitoringtasks.list(
    workspace=..., monitoring_site=..., latest_run_status=...,
    datastream=..., rule_type=...,
) -> HydroServerCollection[MonitoringTask]
hs_api.monitoringtasks.get(uid) -> MonitoringTask
hs_api.monitoringtasks.create(
    name, monitoring_site, description=None, recipients=None,
    crontab=None, interval=None, interval_period=None,
    start_time=None, enabled=True, uid=None
) -> MonitoringTask
hs_api.monitoringtasks.update(
    uid, name=..., description=..., recipients=..., crontab=..., interval=...,
    interval_period=..., start_time=..., enabled=...
) -> MonitoringTask
hs_api.monitoringtasks.delete(uid) -> None
```

#### Run methods

Same as ETL Tasks: `trigger()`, `list_runs(...)`, `get_run(run_id)`.

---

### Monitoring Rules

**Property:** `hs_api.monitoringrules`

Each rule belongs to a monitoring task and checks one datastream.

#### MonitoringRule properties

| Property | Type | Editable | Notes |
|---|---|---|---|
| `uid` | `UUID` | No | |
| `task_id` | `UUID` | No | |
| `datastream_id` | `UUID` | No | |
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
hs_api.monitoringrules.list(task=..., workspace=..., datastream=..., rule_type=...) -> HydroServerCollection[MonitoringRule]
hs_api.monitoringrules.get(uid) -> MonitoringRule
hs_api.monitoringrules.create(
    task_id, datastream, rule_type,
    min_value=None, max_value=None,
    window_interval=None, window_interval_units=None,
    uid=None
) -> MonitoringRule
hs_api.monitoringrules.update(uid, min_value=..., max_value=..., window_interval=..., window_interval_units=...) -> MonitoringRule
hs_api.monitoringrules.delete(uid) -> None
```

To get the datastream a rule checks, use `hs_api.datastreams.get(rule.datastream_id)`.

---

## Quality Control

`HydroServerQualityControl` provides quality-control operations on a pandas DataFrame of observations. It works entirely locally — it doesn't read from or write to HydroServer. Fetch observations first, edit them, then load the result back with `load_observations`.

```python
from hydroserverpy import HydroServerQualityControl

df = datastream.get_observations(fetch_all=True).dataframe
qc_df = df.rename(columns={"phenomenon_time": "timestamp", "result": "value"})[["timestamp", "value"]]

qc = HydroServerQualityControl(datastream_id=datastream.uid, observations=qc_df)
qc.change_values(index_list=[0, 1], operator="MULT", value=0.3048)
corrected = qc.observations
```

The DataFrame must have a datetime `timestamp` column and a float `value` column. Edits are applied to the object's copy; read the result from `qc.observations`.

| Method | Description |
|---|---|
| `filter(data_filter)` | Restrict `observations` to rows matching filters, e.g. `{"GT": 10.0, "LTE": 20.0}` (operations `LT`, `LTE`, `GT`, `GTE`, `E`) |
| `find_gaps(time_value, time_unit)` | Return rows that follow a gap longer than the given duration |
| `fill_gap(gap, fill, interpolate_values)` | Fill gaps longer than `gap` with points every `fill` (both `(value, unit)` tuples), optionally interpolating their values |
| `add_points(points, index=None)` | Insert `[timestamp, value]` points |
| `change_values(index_list, operator, value)` | Apply `MULT`, `DIV`, `ADD`, `SUB`, or `ASSIGN` to the values at the given row indices |
| `delete_points(index_list)` | Delete the rows at the given indices |
| `shift_points(index_list, time_value, time_unit)` | Shift the timestamps of the given rows |
| `interpolate(index_list)` | Replace the given rows' values by linear interpolation |
| `drift_correction(start, end, gap_width)` | Apply a linear drift correction across a row index range |

Time units are `"s"`, `"m"`, `"h"`, `"D"`, `"W"`, `"M"`, and `"Y"`.
