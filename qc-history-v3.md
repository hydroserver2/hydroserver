# HydroServer QC App History Design and Functional Specifications

**Last Updated**: June 8, 2026

---

## 1. Introduction

The HydroServer data quality control (QC) web application provides a web-based graphical user interface (GUI) within which a user can select a HydroServer datastream for editing and perform manual edits on that datastream to produce a new, quality-controlled datastream. Edits may include deleting erroneous values, inserting values, interpolating values, adjusting values, drift corrections, etc. Edited data are saved to a managed datastream that is derived from an original, unmodified source datastream.

The main GUI includes a time series plot of the data where the user can interact with, select, and modify data values. A tabular view of selected data is also provided. Users may optionally enable QC history tracking for a managed datastream, which provides a saved record of all edits made through any instance of the QC app. The history also defines the source datastream, allowing users to view and reconstruct changes over time from the source to the managed datastream.

This document describes the design and functional specifications for QC histories and edit sessions stored in the HydroServer database.

---

## 2. Definitions

**Datastream**: A time series of data values for a particular observed property, at a particular monitoring site, observed using a particular sensor, recorded using a particular unit of measure, and having a particular processing level.

**Edit Event**: An individual action taken by a user that performs a specific operation on a selected set of data values. Examples include delete, insert, adjust, interpolate, drift correct, and flag. Edit events correspond to QC functions in the hydroserverpy package and in the JavaScript functions within the HydroServer QC Web App.

**Edit Session**: A set of Edit Events performed on a selected time range of a managed datastream by an individual HydroServer user.

**History**: A recorded set of edit sessions and their corresponding edit events that have been performed on a managed datastream, organized as a directed acyclic graph (DAG). The history records how transformations on a source datastream have produced the managed datastream in its current state.

**Managed Datastream**: The datastream being managed by the QC app. QC history is associated with this datastream, and edited observations are saved to it. All observations in a managed datastream must be created through committed QC edit sessions.

**Processing Level**: An attribute of a datastream indicating the level of quality control or processing to which a datastream has been subjected (e.g., "raw" data versus "quality controlled" data).

**Selection Event**: An individual action taken by a user that selects a set of data values on which an edit will be performed. Selections may or may not include contiguous data values. Selections may be made by clicking on points, using box or lasso selection tools, or running filters that select data values based on user-defined rules.

**Source Datastream**: A datastream that contains the original, unedited observations from which a managed datastream is derived. Typically this is a raw datastream recorded by a sensor in the field, but it may be any datastream used as a reference for QC editing.

**Version**: A copy of a datastream produced from a source datastream having a different processing level than the source datastream.

---

## 3. Constraints

HydroServer's data model uses processing levels to indicate the level of quality control applied to a datastream and to support datastream versioning. A common convention is processing level 0 for raw data and processing level 1 for quality-controlled data, but HydroServer does not constrain the processing levels that organizations can define. The QC App therefore cannot make assumptions about the meaning of processing levels or that they follow a numeric progression.

To address this, the QC App adopts the concepts of a "managed datastream" and a "source datastream." The managed datastream is the datastream the QC app edits. The source datastream provides an unedited reference copy of the data. A managed datastream and its source datastream must have different processing levels.

A managed datastream can have at most one QC history. This is enforced at the database level within the QC app's data model. A source datastream may serve as the source for any number of managed datastreams.

HydroServer does not enforce source datastream immutability at the API level. Instead, the QC app stores checksums with each session and with the overall history that can be compared against the current state of the source and managed datastreams. If a checksum mismatch is detected, the QC app warns the user that an unrecorded change has occurred. Maintaining QC history integrity ultimately depends on appropriate workspace permissions and organizational policies.

---

## 4. Session-Based History Design

A QC history is represented as a directed acyclic graph (DAG) where each node is a committed edit session and edges represent dependency relationships between sessions. Dependencies are automatically determined by time range overlap: when a new session is committed that covers a time range overlapping with previously committed sessions, it declares those sessions as its dependencies.

The source datastream is the root of the graph. The current state of the managed datastream represents the result of applying all committed sessions to the source datastream in dependency order.

Sessions do not need to be contiguous in time. A user may create a session for July data without first covering June. Gaps in the history are permitted. However, sessions must be executed in dependency order: when reconstructing the managed datastream for a given time window, all upstream committed sessions that overlap that window must be applied first.

When a user begins an edit session over a time range that has no prior committed sessions, the QC app fetches observations from the source datastream for the user to edit. When a user begins an edit session over a time range that overlaps with previously committed sessions, the QC app fetches observations from the managed datastream for the overlapping portion and from the source datastream for any non-overlapping portion. The source datastream's observations are never directly edited by the QC app.

Only one in-progress (uncommitted) session is permitted per managed datastream at a time.

---

## 5. Creating and Modifying a QC History for a Datastream

A QC history can be created for a datastream in the HydroServer QC App using the following steps:

1. From the QC App's "Select" tab, a user selects one or more datastreams (up to five) to plot. Any datastream for which the user has view permission can be plotted. Existing source and managed datastreams are clearly marked.
2. To create a new managed datastream, users click "Create Datastream for Editing," which opens a form:
   1. Users choose a source datastream.
   2. All form fields are populated with the source datastream's metadata.
   3. Users must select a different processing level for the managed datastream, and may optionally edit other metadata.
   4. Once finished, users click "Create Datastream."
   5. The QC App creates the managed datastream in HydroServer, creates an empty QC history linked to it, and tags the source datastream with a reference to the managed datastream.
3. Once added to the plot, the user selects the managed datastream for editing and switches to the "Edit" tab.
4. On the "Edit" tab, all edits must occur within an edit session:
   1. If an in-progress session already exists, that session is opened.
   2. If no active session exists, the user clicks "Start New Edit Session." A form prompts the user to enter the phenomenon time range for the session and an optional description. The QC App saves the in-progress session to the history and the user begins editing.
   3. For new sessions covering time ranges not yet in the managed datastream, the QC App fetches the source datastream observations for that time range. A "Copy data from source" operation may be automated for time ranges with source data but no committed session.
5. Each time a user selects data values and applies an edit tool (delete, insert, adjust, interpolate, flag, etc.), the data in the plot updates to reflect the edit, and a new edit event is appended to the in-progress session.
6. When the user is finished, they commit the session. The QC App performs integrity checks, pushes the edited observations to the managed datastream, and updates the session record to Committed.

---

## 6. Edit Session States

The QC App supports two states for an edit session:

1. **In Progress**: The session is recorded in the QC history but its observations have not yet been saved to the managed datastream. Only one in-progress session is permitted per managed datastream at a time.
2. **Committed**: The session has been recorded in the QC history and its edited observations have been materialized in the managed datastream.

---

## 7. Business Rules

### 7.1. Datastream Relationships

1. Each managed datastream will have exactly one source datastream and at most one QC history. This is enforced at the database level.
2. A QC history encodes the ID of the source datastream and is linked to the managed datastream. The managed datastream and its history are created together by the QC App.
3. Source datastreams are tagged with a reference to any linked managed datastream(s) using HydroServer's tagging system. The presence of this tag signals to the QC App that the datastream is being used as a source, and the QC App will disallow editing it through the QC interface.
4. HydroServer does not enforce source datastream immutability. Checksums are used to detect unrecorded changes rather than prevent them.
5. Observations in a managed datastream may only be created or modified through committed QC edit sessions. Any external modification to a managed datastream within a committed time range will be detected via checksum mismatch on the next integrity check.
6. A source datastream may serve as the source for any number of managed datastreams and histories.

### 7.2. Edit Sessions and History

1. A history contains zero or more committed edit sessions, organized as a DAG.
2. Edit session dependencies are automatically computed at session creation based on time range overlap with previously committed sessions. An in-progress session does not affect the dependencies of other sessions.
3. An edit session represents a unit of work by a single user and has the following attributes:
   - A single user who created the session.
   - The datetime the session was created.
   - A phenomenon time range defined by a start and end datetime.
   - An ordered list of edit events performed during the session.
   - A status (In Progress or Committed) and the datetime that status was assigned.
   - An optional description.
   - A source checksum recorded at session creation over the session's phenomenon time range.
   - A managed checksum recorded at commit time over the session's phenomenon time range.
4. The end datetime of an edit session's phenomenon time range cannot extend past the current end of the source datastream. This prevents the session from referencing data that does not yet exist.
5. Each edit event within a session has the following attributes:
   - Event type (e.g., delete, insert, adjust, interpolate, drift correct, flag).
   - The set of data values affected, identified by phenomenon time.
   - The datetime the event was performed.
   - Type-specific parameters (e.g., interpolation method, adjustment value, drift rate).
   - An optional comment.
6. Edit events within a session are executed in the order they were recorded.

### 7.3. Rollback and Correction

Committed sessions are never deleted or modified. Rolling back unwanted changes is accomplished by creating a new edit session that covers the same time range and applies the corrected edits. When this correction session is committed, its replace operation overwrites the managed datastream observations for that time range with the corrected data. The full edit history is preserved, including the original and the correction. This is the preferred approach.

Users may also undo uncommitted changes within an in-progress session by discarding the in-progress session and starting a new one.

### 7.4. Checksums and Integrity

A datastream checksum is computed for a subset of observations defined by a phenomenon time range. The checksum is derived from the count of observations in that range and the ID of the most recently inserted observation in that range. Because observations can only be deleted or replaced (not edited in place), this checksum reliably detects any insertion or deletion within the specified time range.

Three checksums are maintained:

- **History source checksum**: Stored on the history record. Covers the source datastream over the full committed phenomenon time range of the history. Updated on each successful commit.
- **History managed checksum**: Stored on the history record. Covers the managed datastream over the full committed phenomenon time range of the history. Updated on each successful commit.
- **Session source checksum**: Stored on each session. Covers the source datastream over the session's phenomenon time range. Recorded at session creation and never updated.
- **Session managed checksum**: Stored on each session. Covers the managed datastream over the session's phenomenon time range. Recorded at commit time.

Integrity checks are performed:
- When a user opens or resumes an in-progress session.
- When a user attempts to commit a session.
- On demand via the QC App UI.

If the current source checksum over the session's time range differs from the stored session source checksum, the user is warned that the source data has been modified since the session was created. They must review their edits against the updated source data before committing.

If the current managed checksum over the session's time range differs from the stored session managed checksum (at commit time), the user is warned that the managed datastream was modified outside the QC history. The user must resolve the discrepancy before the commit can proceed.

---

## 8. Data Model

The following Django models form the QC history data model. These models live in the `quality` app.

### QCHistory

Represents the linkage between a source datastream and a managed datastream and serves as the root record for all sessions.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key. |
| `managed_datastream` | FK → Datastream (unique) | The managed datastream. Unique constraint enforces one history per managed datastream. |
| `source_datastream` | FK → Datastream | The source datastream. |
| `created_by` | FK → User | The user who created the history. |
| `created_at` | DateTime | When the history was created. |
| `description` | Text (nullable) | Optional description of the history. |
| `phenomenon_time_start` | DateTime (nullable) | Start of the full committed time range. Null if no sessions have been committed. |
| `phenomenon_time_end` | DateTime (nullable) | End of the full committed time range. Null if no sessions have been committed. |
| `source_checksum` | CharField (nullable) | Checksum of the source datastream over the full committed time range. Updated on each commit. |
| `managed_checksum` | CharField (nullable) | Checksum of the managed datastream over the full committed time range. Updated on each commit. |

### QCSession

Represents a single unit of work within a history.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key. |
| `history` | FK → QCHistory | The parent history. |
| `created_by` | FK → User | The user who created the session. |
| `created_at` | DateTime | When the session was created. |
| `phenomenon_time_start` | DateTime | Start of the session's phenomenon time range. |
| `phenomenon_time_end` | DateTime | End of the session's phenomenon time range. |
| `status` | CharField | `in_progress` or `committed`. |
| `committed_at` | DateTime (nullable) | When the session was committed. Null if not yet committed. |
| `description` | Text (nullable) | Optional description of the session's purpose. |
| `source_checksum` | CharField | Checksum of source datastream over the session's time range, recorded at session creation. |
| `managed_checksum` | CharField (nullable) | Checksum of managed datastream over the session's time range, recorded at commit time. |

**Constraint**: At most one session per history may have `status = in_progress`. Enforced at the application level.

### QCSessionDependency

Represents a directed edge in the history DAG. An edge from session A to session B means session B depends on session A.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key. |
| `session` | FK → QCSession | The downstream session (the dependent). |
| `dependency` | FK → QCSession | The upstream session (the dependency). |

Dependencies are computed automatically at session creation based on time range overlap with all previously committed sessions. Only committed sessions are recorded as dependencies.

**Unique constraint**: `(session, dependency)`.

### QCOperation

Represents a single operation within a session. Operations are ordered and executed sequentially. Operation types correspond directly to the `qc-utils` library enums.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key. |
| `session` | FK → QCSession | The parent session. |
| `order` | PositiveInteger | Execution order within the session. Unique per session. |
| `operation_type` | CharField (choices: `OperationType`) | One of the operation type values listed below. |
| `created_at` | DateTime | When the operation was recorded. |
| `comment` | Text (nullable) | Optional user comment explaining the operation. |
| `arguments` | JSONField | Maps directly to the `args` field in `qc-utils`. For `SELECTION` operations, `arguments` contains the explicit user-provided timestamps. For all other filter operations, `arguments` contains the filter criteria used to compute the selection on replay. |

**Unique constraint**: `(session, order)`.

**On selection replay**: Filter operations do not store their resolved output. On replay, filter criteria are re-executed against the source or managed datastream data to recompute the selection. Edit operations locate their selection by finding the nearest preceding filter operation row by `order` and re-running it.

#### Enums

The following enums are sourced directly from `qc-utils` and used in `operation_type` and `parameters` fields.

**`OperationType`** — valid values for `QCOperation.operation_type`:

| Category | Value |
|---|---|
| Filter | `SELECTION` |
| Filter | `VALUE_THRESHOLD` |
| Filter | `DATETIME_RANGE` |
| Filter | `CHANGE` |
| Filter | `RATE_OF_CHANGE` |
| Filter | `FIND_GAPS` |
| Filter | `PERSISTENCE` |
| Edit | `ADD_POINTS` |
| Edit | `CHANGE_VALUES` |
| Edit | `ASSIGN_VALUES_BULK` |
| Edit | `DELETE_POINTS` |
| Edit | `DRIFT_CORRECTION` |
| Edit | `INTERPOLATE` |
| Edit | `SHIFT_DATETIMES` |
| Edit | `FILL_GAPS` |
| Edit | `ASSIGN_DATETIMES_BULK` |

**`Operator`** — used in `CHANGE_VALUES` parameters:

| Value | Description |
|---|---|
| `ADD` | Add value to result |
| `SUB` | Subtract value from result |
| `MULT` | Multiply result by value |
| `DIV` | Divide result by value |
| `ASSIGN` | Replace result with value |

**`Comparator`** — used in `VALUE_THRESHOLD`, `CHANGE`, and `RATE_OF_CHANGE` parameters:

| Value | Description |
|---|---|
| `LT` | Less than |
| `LTE` | Less than or equal to |
| `GT` | Greater than |
| `GTE` | Greater than or equal to |
| `E` | Equal |

**`TimeUnit`** — used in `SHIFT_DATETIMES`, `FILL_GAPS`, and `FIND_GAPS` parameters:

| Value | Description |
|---|---|
| `s` | Second |
| `m` | Minute |
| `h` | Hour |
| `D` | Day |
| `W` | Week |
| `M` | Month |
| `Y` | Year |

#### Operation types and parameters

Operations are divided into two categories matching the `qc-utils` library: **filter operations** that produce a selection, and **edit operations** that act on a selection or on explicit data.

**Filter operations** — produce a `selection` output stored on the row.

| `operation_type` | `arguments` schema | Description |
|---|---|---|
| `SELECTION` | `{"timestamps": ["<iso8601>", ...]}` | Explicit user-provided selection. Timestamps are provided directly as input parameters. |
| `VALUE_THRESHOLD` | `{"comparators": {"GT"?: n, "GTE"?: n, "LT"?: n, "LTE"?: n, "E"?: n}, "range"?: ["<iso8601>", "<iso8601>"]}` | Selects observations whose result value matches the given comparator(s). |
| `DATETIME_RANGE` | `{"start"?: "<iso8601>", "end"?: "<iso8601>"}` | Selects observations within a phenomenon time window. |
| `CHANGE` | `{"comparator": "Comparator", "value": n, "range"?: ["<iso8601>", "<iso8601>"]}` | Selects observations where the step change (Y[i] − Y[i−1]) matches the comparator. |
| `RATE_OF_CHANGE` | `{"comparator": "Comparator", "fraction": n, "range"?: ["<iso8601>", "<iso8601>"]}` | Selects observations where the fractional step change matches the comparator. |
| `FIND_GAPS` | `{"amount": n, "unit": "TimeUnit", "range"?: ["<iso8601>", "<iso8601>"]}` | Selects observations preceded by a gap exceeding the threshold. |
| `PERSISTENCE` | `{"times": n, "range"?: ["<iso8601>", "<iso8601>"]}` | Selects observations that are part of a run of equal consecutive values of at least `times` length. |

**Edit operations** — transform data. Selection-consuming operations locate their selection from the nearest preceding filter operation by `order`.

| `operation_type` | `arguments` schema | Uses selection? | Description |
|---|---|---|---|
| `DELETE_POINTS` | `{}` | Yes | Deletes all observations in the selection. |
| `CHANGE_VALUES` | `{"operator": "Operator", "value": n}` | Yes | Applies arithmetic to the result of each observation in the selection. |
| `ASSIGN_VALUES_BULK` | `{"values": [n, ...]}` | Yes | Assigns values in order to each observation in the selection. |
| `INTERPOLATE` | `{}` | Yes | Linearly interpolates across consecutive groups in the selection. |
| `DRIFT_CORRECTION` | `{"value": n}` | Yes | Applies a linear drift correction across consecutive groups in the selection. |
| `SHIFT_DATETIMES` | `{"amount": n, "unit": "TimeUnit"}` | Yes | Shifts phenomenon timestamps of observations in the selection by the given offset. |
| `ASSIGN_DATETIMES_BULK` | `{"datetimes": ["<iso8601>", ...]}` | Yes | Assigns phenomenon timestamps in order to each observation in the selection. |
| `ADD_POINTS` | `{"values": [{"phenomenon_time": "<iso8601>", "result": n}, ...]}` | No | Inserts new observations at the specified times and values. |
| `FILL_GAPS` | `{"gap_amount": n, "gap_unit": "TimeUnit", "fill_amount": n, "fill_unit": "TimeUnit", "interpolate": bool, "fill_value": n, "range"?: ["<iso8601>", "<iso8601>"]}` | No | Detects gaps exceeding the threshold and inserts observations at the given cadence. |

---

## 9. Committing Sessions

Committing a session is a two-step process performed by the QC App:

**Step 1 — Push observations** (QC App → observations API):

The QC App sends the edited observations to the managed datastream via a `bulk-create` replace operation. This deletes all existing managed datastream observations within the session's phenomenon time range and inserts the session's output observations. Large observation sets may be uploaded in chunks. Session operations are already saved to the session record incrementally via PATCH and do not need to be sent again.

**Step 2 — Commit** (QC App → `/commit`):

The QC App calls the commit endpoint with no request body. The server then:

1. **Integrity check — source datastream**: Fetch the current checksum of the source datastream over the session's phenomenon time range and compare it against the session's stored `source_checksum`. If they differ, return an error indicating the source data has changed since the session was created.
2. **Integrity check — managed datastream**: Fetch the current checksum of the managed datastream over the session's phenomenon time range and compare it against the history's `managed_checksum` for that range. If they differ, return an error indicating the managed datastream was modified outside the QC history.
3. **Update session record**: Set `status = committed`, set `committed_at` to the current datetime, and record the new `managed_checksum` over the session's phenomenon time range.
4. **Update history record**: Extend `phenomenon_time_start` and `phenomenon_time_end` to cover the newly committed time range (if applicable) and update `source_checksum` and `managed_checksum` to cover the full committed time range.
5. **Compute dependencies**: Query all previously committed sessions whose phenomenon time ranges overlap this session's range and create `QCSessionDependency` records.

If the commit endpoint returns an error after observations have already been pushed (Step 1), the inconsistency is self-correcting: the session remains `in_progress`, the QC App can surface the error to the user, and the user retries once the issue is resolved. The integrity checks will pass on retry as long as no further changes are made to the managed datastream between attempts.

---

## 10. API Endpoints

The HydroServer QC App retrieves and manages histories and sessions via dedicated endpoints in the HydroServer Data Management API. Other software tools may also use these endpoints.

A history and its sessions are publicly accessible if both the source and managed datastreams are in public workspaces. Otherwise, access requires view permission on the managed datastream's workspace. Creating or modifying a history or session requires edit permission on the managed datastream's workspace.

### 10.1. QC History

#### GET/POST /quality-control/histories

- **GET**: Retrieve all histories the authenticated user has permission to view, plus all public histories. Filterable by `managed_datastream_id` and `source_datastream_id`.
- **POST**: Create a new QC history. Request body must include `managed_datastream_id`, `source_datastream_id`, and optional `description`. Fails if the managed datastream already has a history.

#### GET/PATCH/DELETE /quality-control/histories/{history_id}

- **GET**: Retrieve the history with the given ID, including `phenomenon_time_start`, `phenomenon_time_end`, checksum fields, and summary session counts.
- **PATCH**: Update the history. Editable fields: `description`.
- **DELETE**: Delete the history and all associated sessions. Does not delete the managed or source datastreams. Only permitted if the history has no committed sessions, or if the user explicitly confirms deletion of an active history.

### 10.2. QC Sessions

#### GET/POST /quality-control/histories/{history_id}/sessions

- **GET**: Retrieve all sessions associated with the given history. Filterable by `status`, `phenomenon_time_start`, and `phenomenon_time_end`.
- **POST**: Create a new in-progress session. Request body must include `phenomenon_time_start`, `phenomenon_time_end`, and optional `description`. Fails if an in-progress session already exists for this history. Records the `source_checksum` at creation time.

#### GET/PATCH/DELETE /quality-control/histories/{history_id}/sessions/{session_id}

- **GET**: Retrieve session details including `status`, time range, checksum fields, resolved dependencies, and associated operations.
- **PATCH**: Update the session. Editable fields: `description`, `operations`. Only in-progress sessions can be edited.
- **DELETE**: Delete the session. Only in-progress sessions can be deleted.

#### POST /quality-control/histories/{history_id}/sessions/{session_id}/commit

- **POST**: Commit the session. No request body. Observations must already have been pushed to the managed datastream via the observations API before calling this endpoint. The server performs integrity checks, updates session and history records, and computes session dependencies. Returns the updated session record on success or a descriptive error on failure.

### 10.3. Observations (checksum support)

Observation endpoints that return collections include a checksum value in the `X-Observation-Checksum` response header computed over the returned subset. The QC App uses this to verify source and managed datastream integrity.

#### GET /datastreams/{datastream_id}/observations

- As currently specified. Checksum is included in the response header for the returned subset.

#### POST /datastreams/{datastream_id}/observations/bulk-create

- Supports `append`, `insert`, `backfill`, and `replace` modes (as currently specified).

#### POST /datastreams/{datastream_id}/observations/bulk-delete

- Deletes all observations within a given phenomenon time range.

#### GET/PATCH/DELETE /datastreams/{datastream_id}/observations/{observation_id}

- Standard single-observation endpoints (as currently specified).