# How to Manage Data with the HydroServer TypeScript Client

To perform data management operations, initialize a HydroServer client once at app startup.

```ts
import hs, { createHydroServer } from "@hydroserver/client";

await createHydroServer({
  host: "https://playground.hydroserver.org",
});
```

If your frontend is served from the same domain as HydroServer, set `host: ""` to use same-origin requests.

```ts
await createHydroServer({ host: "" });
```

The TypeScript client exposes these core services:

- `workspaces`
- `things`
- `datastreams`
- `sensors`
- `units`
- `processingLevels`
- `observedProperties`
- `resultQualifiers`
- `orchestrationSystems`
- `dataConnections`
- `tasks`

## Responses and errors

Most methods return an `ApiResponse<T>` object:

- `ok`: request success flag
- `data`: response payload
- `status`: HTTP status
- `message`: best-available status/error text
- `meta`: optional metadata

```ts
const res = await hs.workspaces.list();
if (!res.ok) {
  console.error(res.message);
} else {
  console.log(res.data);
}
```

## Collections

All core collection services support:

- `list(params)`: returns `ApiResponse<T[]>`
- `listItems(params)`: returns `T[]` (or `[]` on error)
- `listAllItems(params)`: fetches and merges all pages

Most endpoints support query params such as:

- `page`
- `page_size`
- `order_by`
- `expand_related`
- Resource-specific filters

### Example: Access collection items

```ts
const workspaces = await hs.workspaces.listItems();
for (const workspace of workspaces) {
  console.log(workspace.name);
}
```

### Example: Collection pagination

```ts
// Fetch page 2 only
const page2 = await hs.workspaces.list({
  page: 2,
  page_size: 5,
});

// Fetch all pages
const allWorkspaces = await hs.workspaces.listAllItems({
  is_associated: true,
});
```

### Example: Collection ordering

```ts
const ordered = await hs.workspaces.list({
  order_by: ["name"],
});

const multiOrdered = await hs.workspaces.list({
  order_by: ["-name", "isPrivate"],
});
```

### Example: Collection filtering

```ts
const publicWorkspaces = await hs.workspaces.listAllItems({
  is_private: false,
});

const yourPrivateWorkspaces = await hs.workspaces.listAllItems({
  is_private: true,
  is_associated: true,
});
```

## Authentication and session

```ts
const loginRes = await hs.session.login("user@example.com", "password");
if (!loginRes.ok) {
  console.error(loginRes.message);
}

if (hs.session.isAuthenticated) {
  console.log("Logged in");
}

hs.on("session:expired", () => {
  console.log("Session expired");
});

await hs.session.logout();
```

## Workspaces

Workspaces are the top-level access-control boundary for HydroServer data.

### Example: Get workspaces

```ts
const publicWorkspaces = await hs.workspaces.listAllItems();

const yourWorkspaces = await hs.workspaces.listAllItems({
  is_associated: true,
});

const workspace = await hs.workspaces.getItem(
  "00000000-0000-0000-0000-000000000000"
);
```

### Example: Create a workspace

```ts
import { Workspace } from "@hydroserver/client";

const workspace = new Workspace();
workspace.name = "New Workspace";
workspace.isPrivate = false;

const created = await hs.workspaces.create(workspace);
```

### Example: Modify a workspace

```ts
const workspace = await hs.workspaces.getItem(
  "00000000-0000-0000-0000-000000000000"
);
if (!workspace) throw new Error("Workspace not found");

workspace.name = "Updated Workspace Name";
workspace.isPrivate = true;

await hs.workspaces.update(workspace);
```

### Example: Manage collaborators and ownership transfer

```ts
const workspaceId = "00000000-0000-0000-0000-000000000000";
const userEmail = "user@example.com";
const roleId = "11111111-1111-1111-1111-111111111111";

await hs.workspaces.addCollaborator(workspaceId, userEmail, roleId);
await hs.workspaces.updateCollaboratorRole(workspaceId, userEmail, roleId);
await hs.workspaces.removeCollaborator(workspaceId, userEmail);

await hs.workspaces.transferOwnership(workspaceId, "new-owner@example.com");
await hs.workspaces.acceptOwnershipTransfer(workspaceId);
await hs.workspaces.rejectOwnershipTransfer(workspaceId);
```

## Things (Sites)

Things represent physical monitoring locations.

### Example: Get things

```ts
const publicThings = await hs.things.listAllItems();

const workspaceThings = await hs.things.listAllItems({
  workspace_id: ["00000000-0000-0000-0000-000000000000"],
});

const boundedThings = await hs.things.listAllItems({
  bbox: ["-112.166,41.369,-111.402,42.999"],
});

const filteredThings = await hs.things.listAllItems({
  tag: ["Region:A"],
});
```

### Example: Create a thing

```ts
import { Thing } from "@hydroserver/client";

const thing = new Thing();
thing.workspaceId = "00000000-0000-0000-0000-000000000000";
thing.name = "My Site";
thing.description = "This site records environmental observations.";
thing.samplingFeatureType = "Site";
thing.samplingFeatureCode = "OBSERVATION_SITE";
thing.siteType = "Atmosphere";
thing.location.latitude = 41.739;
thing.location.longitude = -111.7957;
thing.location.elevation_m = 1414;
thing.location.elevationDatum = "EGM96";
thing.location.adminArea1 = "UT";
thing.location.adminArea2 = "Cache";
thing.location.country = "US";
thing.dataDisclaimer = "Data may be provisional and subject to revision.";
thing.isPrivate = false;

await hs.things.create(thing);
```

### Example: Modify thing metadata and privacy

```ts
const thing = await hs.things.getItem("00000000-0000-0000-0000-000000000000");
if (!thing) throw new Error("Thing not found");

thing.name = "Updated Site Name";
thing.description = "Updated site metadata";
await hs.things.update(thing);

await hs.things.updatePrivacy(thing.id, true);
```

### Example: Manage thing tags

```ts
const thingId = "00000000-0000-0000-0000-000000000000";

await hs.things.createTag(thingId, { key: "Region", value: "A" });
await hs.things.updateTag(thingId, { key: "Region", value: "B" });
await hs.things.deleteTag(thingId, { key: "Region" });
```

### Example: Manage thing file attachments

```ts
const thingId = "00000000-0000-0000-0000-000000000000";
const data = new FormData();
data.append("file", fileInput.files![0]);

await hs.things.uploadAttachments(thingId, data);
await hs.things.getAttachments(thingId);
await hs.things.deleteAttachment(thingId, "site-photo.png");
```

### Example: Get datastreams for a thing

```ts
const thingDatastreams = await hs.datastreams.listAllItems({
  thing_id: ["00000000-0000-0000-0000-000000000000"],
});
```

### Example: Delete a thing

```ts
await hs.things.delete("00000000-0000-0000-0000-000000000000");
```

## Observed Properties

### Example: Get observed properties

```ts
const observedProperties = await hs.observedProperties.listAllItems();

const workspaceObservedProperties = await hs.observedProperties.listAllItems({
  workspace_id: ["00000000-0000-0000-0000-000000000000"],
});
```

### Example: Create and modify an observed property

```ts
import { ObservedProperty } from "@hydroserver/client";

const observedProperty = new ObservedProperty();
observedProperty.workspaceId = "00000000-0000-0000-0000-000000000000";
observedProperty.name = "Temperature";
observedProperty.definition = "Air temperature";
observedProperty.description = "Near-surface air temperature";
observedProperty.type = "Climate";
observedProperty.code = "AirTemp";

const created = await hs.observedProperties.createItem(observedProperty);
if (!created) throw new Error("Unable to create observed property");

created.name = "Air Temperature";
await hs.observedProperties.update(created);
```

### Example: Delete an observed property

```ts
await hs.observedProperties.delete("00000000-0000-0000-0000-000000000000");
```

## Units

### Example: Create and modify a unit

```ts
import { Unit } from "@hydroserver/client";

const unit = new Unit();
unit.workspaceId = "00000000-0000-0000-0000-000000000000";
unit.name = "Degree Celsius";
unit.symbol = "C";
unit.definition = "Degree Celsius";
unit.type = "Temperature";

const created = await hs.units.createItem(unit);
if (!created) throw new Error("Unable to create unit");

created.name = "Celsius";
await hs.units.update(created);
```

### Example: Delete a unit

```ts
await hs.units.delete("00000000-0000-0000-0000-000000000000");
```

## Sensors

### Example: Create and modify a sensor

```ts
import { Sensor } from "@hydroserver/client";

const sensor = new Sensor();
sensor.workspaceId = "00000000-0000-0000-0000-000000000000";
sensor.name = "Environmental Sensor";
sensor.description = "Records environmental observations.";
sensor.encodingType = "application/json";
sensor.manufacturer = "Campbell Scientific";
sensor.model = "A";
sensor.modelLink = "https://example.com/sensors/A";
sensor.methodType = "Sensor";
sensor.methodLink = "https://example.com/methods/sensor";
sensor.methodCode = "SENSOR_A";

const created = await hs.sensors.createItem(sensor);
if (!created) throw new Error("Unable to create sensor");

created.name = "Environmental Sensor - Updated";
await hs.sensors.update(created);
```

### Example: Delete a sensor

```ts
await hs.sensors.delete("00000000-0000-0000-0000-000000000000");
```

## Processing Levels

### Example: Create and modify a processing level

```ts
import { ProcessingLevel } from "@hydroserver/client";

const processingLevel = new ProcessingLevel();
processingLevel.workspaceId = "00000000-0000-0000-0000-000000000000";
processingLevel.code = "0";
processingLevel.definition = "Raw";
processingLevel.explanation =
  "Data have not been processed or quality controlled.";

const created = await hs.processingLevels.createItem(processingLevel);
if (!created) throw new Error("Unable to create processing level");

created.code = "1";
await hs.processingLevels.update(created);
```

### Example: Delete a processing level

```ts
await hs.processingLevels.delete("00000000-0000-0000-0000-000000000000");
```

## Result Qualifiers

### Example: Create and modify a result qualifier

```ts
import { ResultQualifier } from "@hydroserver/client";

const resultQualifier = new ResultQualifier();
resultQualifier.workspaceId = "00000000-0000-0000-0000-000000000000";
resultQualifier.code = "PF";
resultQualifier.description = "Power Failure";

const created = await hs.resultQualifiers.createItem(resultQualifier);
if (!created) throw new Error("Unable to create result qualifier");

created.code = "PF2";
await hs.resultQualifiers.update(created);
```

### Example: Delete a result qualifier

```ts
await hs.resultQualifiers.delete("00000000-0000-0000-0000-000000000000");
```

## Datastreams

Datastreams group observations for one observed property, measured by one sensor, at one thing.

### Example: Get datastreams

```ts
const datastreams = await hs.datastreams.listAllItems();

const workspaceDatastreams = await hs.datastreams.listAllItems({
  workspace_id: ["00000000-0000-0000-0000-000000000000"],
});

const thingDatastreams = await hs.datastreams.listAllItems({
  thing_id: ["00000000-0000-0000-0000-000000000000"],
});

const datastream = await hs.datastreams.getItem(
  "00000000-0000-0000-0000-000000000000"
);
```

### Example: Create and modify a datastream

```ts
import { Datastream } from "@hydroserver/client";

const datastream = new Datastream();
datastream.workspaceId = "00000000-0000-0000-0000-000000000000";
datastream.thingId = "11111111-1111-1111-1111-111111111111";
datastream.sensorId = "22222222-2222-2222-2222-222222222222";
datastream.observedPropertyId = "33333333-3333-3333-3333-333333333333";
datastream.processingLevelId = "44444444-4444-4444-4444-444444444444";
datastream.unitId = "55555555-5555-5555-5555-555555555555";
datastream.name = "Air Temperature";
datastream.description = "15-minute air temperature";
datastream.sampledMedium = "Air";
datastream.aggregationStatistic = "Continuous";
datastream.noDataValue = -9999;
datastream.timeAggregationInterval = 15;
datastream.timeAggregationIntervalUnit = "minutes";
datastream.intendedTimeSpacing = 15;
datastream.intendedTimeSpacingUnit = "minutes";
datastream.isPrivate = false;
datastream.isVisible = true;

const created = await hs.datastreams.createItem(datastream);
if (!created) throw new Error("Unable to create datastream");

created.name = "Air Temperature (Updated)";
await hs.datastreams.update(created);
```

### Example: Manage datastream tags

```ts
const datastreamId = "00000000-0000-0000-0000-000000000000";

await hs.datastreams.createTag(datastreamId, {
  key: "MaxAllowableResult",
  value: "100",
});

await hs.datastreams.updateTag(datastreamId, {
  key: "MaxAllowableResult",
  value: "120",
});

await hs.datastreams.deleteTag(datastreamId, {
  key: "MaxAllowableResult",
});
```

### Example: Manage datastream file attachments

```ts
const datastreamId = "00000000-0000-0000-0000-000000000000";
const data = new FormData();
data.append("file", fileInput.files![0]);

await hs.datastreams.uploadAttachments(datastreamId, data);
await hs.datastreams.getAttachments(datastreamId);
await hs.datastreams.deleteAttachment(datastreamId, "rating-curve.csv");
```

### Example: Get related metadata for a datastream

```ts
const res = await hs.datastreams.get(
  "00000000-0000-0000-0000-000000000000",
  { expand_related: true }
);

if (res.ok) {
  console.log(res.data.thing);
  console.log(res.data.sensor);
  console.log(res.data.observedProperty);
  console.log(res.data.unit);
  console.log(res.data.processingLevel);
}
```

### Example: Get observations

```ts
const observations = await hs.datastreams.getObservations(
  "00000000-0000-0000-0000-000000000000",
  {
    format: "row",
    order_by: ["phenomenonTime"],
    phenomenon_time_min: "2025-01-01T00:00:00Z",
    phenomenon_time_max: "2025-12-31T23:59:59Z",
    page_size: 1000,
  }
);
```

### Example: Upload observations

```ts
await hs.datastreams.createObservations(
  "00000000-0000-0000-0000-000000000000",
  {
    fields: ["phenomenonTime", "result"],
    data: [
      ["2025-01-26T00:00:00Z", 40.0],
      ["2025-01-27T00:00:00Z", 41.0],
      ["2025-01-28T00:00:00Z", 42.0],
    ],
  }
);
```

### Example: Replace observations in a date range

```ts
await hs.datastreams.createObservations(
  "00000000-0000-0000-0000-000000000000",
  {
    fields: ["phenomenonTime", "result"],
    data: [
      ["2025-01-26T00:00:00Z", 40.0],
      ["2025-01-27T00:00:00Z", 41.0],
      ["2025-01-28T00:00:00Z", 42.0],
    ],
  },
  { mode: "replace" }
);
```

### Example: Delete observations

```ts
const datastreamId = "00000000-0000-0000-0000-000000000000";

// Delete observations in a time range
await hs.datastreams.deleteObservations(datastreamId, {
  phenomenonTimeStart: "2025-01-01T00:00:00Z",
  phenomenonTimeEnd: "2025-12-31T23:59:59Z",
});

// Delete all observations in a datastream
await hs.datastreams.deleteObservations(datastreamId);
```

### Example: Download observations as CSV

```ts
await hs.datastreams.downloadCsv("00000000-0000-0000-0000-000000000000");

await hs.datastreams.downloadCsvBatchZip([
  "00000000-0000-0000-0000-000000000000",
  "11111111-1111-1111-1111-111111111111",
]);
```

### Example: Delete a datastream

```ts
await hs.datastreams.delete("00000000-0000-0000-0000-000000000000");
```

## Orchestration Systems

Orchestration systems represent loaders/processes that run ETL tasks.

### Example: Get orchestration systems

```ts
const systems = await hs.orchestrationSystems.listAllItems({
  workspace_id: ["00000000-0000-0000-0000-000000000000"],
});
```

### Example: Create and modify an orchestration system

```ts
const orchestrationSystem = {
  id: "",
  name: "My Data Loader",
  type: "ETL",
  workspaceId: "00000000-0000-0000-0000-000000000000",
};

const created = await hs.orchestrationSystems.createItem(orchestrationSystem);
if (!created) throw new Error("Unable to create orchestration system");

created.name = "Updated Data Loader";
await hs.orchestrationSystems.update(created);
```

### Example: Delete an orchestration system

```ts
await hs.orchestrationSystems.delete("00000000-0000-0000-0000-000000000000");
```

## Data Connections

Data connections define extract, transform, and load settings used by task runs.

### Example: Get data connections

```ts
const dataConnections = await hs.dataConnections.listAllItems({
  workspace_id: ["00000000-0000-0000-0000-000000000000"],
  expand_related: true,
});
```

### Example: Create and modify a data connection

```ts
import { DataConnection, Workspace } from "@hydroserver/client";

const dataConnection = new DataConnection();
dataConnection.name = "Example Data Connection";

const workspace = new Workspace();
workspace.id = "00000000-0000-0000-0000-000000000000";
dataConnection.workspace = workspace;

dataConnection.extractor.type = "HTTP";
dataConnection.extractor.settings = {
  sourceUri: "https://example.com/data.csv",
  placeholderVariables: [],
};

const created = await hs.dataConnections.createItem(dataConnection);
if (!created) throw new Error("Unable to create data connection");

created.name = "Updated Data Connection";
await hs.dataConnections.update(created);
```

### Example: Delete a data connection

```ts
await hs.dataConnections.delete("00000000-0000-0000-0000-000000000000");
```

## Tasks

Tasks bind orchestration systems, data connections, and payload mappings.

### Example: Get tasks

```ts
const tasks = await hs.tasks.listAllItems({
  workspace_id: ["00000000-0000-0000-0000-000000000000"],
  expand_related: true,
});
```

### Example: Create and modify a task

```ts
import { Task } from "@hydroserver/client";

const task = new Task({
  name: "Example Task",
  workspaceId: "00000000-0000-0000-0000-000000000000",
  dataConnectionId: "11111111-1111-1111-1111-111111111111",
  orchestrationSystemId: "22222222-2222-2222-2222-222222222222",
  mappings: [
    {
      sourceIdentifier: "temperature",
      paths: [
        {
          targetIdentifier: "33333333-3333-3333-3333-333333333333",
          dataTransformations: [],
        },
      ],
    },
  ],
});

const created = await hs.tasks.createItem(task);
if (!created) throw new Error("Unable to create task");

created.name = "Updated Task";
await hs.tasks.update(created);
```

### Example: Trigger a task run

```ts
await hs.tasks.runTask("00000000-0000-0000-0000-000000000000");
```

### Example: Delete a task

```ts
await hs.tasks.delete("00000000-0000-0000-0000-000000000000");
```

## Task Runs

HydroServer stores task run history for ETL execution.

### Example: Get task runs

```ts
const taskId = "00000000-0000-0000-0000-000000000000";

const runs = await hs.tasks.getTaskRuns(taskId, {
  page_size: 50,
  order_by: ["-startedAt"],
});

const run = await hs.tasks.getTaskRun(
  taskId,
  "11111111-1111-1111-1111-111111111111"
);
```

### Example: Create a task run (external orchestration reporting)

```ts
await hs.tasks.createTaskRun("00000000-0000-0000-0000-000000000000", {
  status: "SUCCESS",
  startedAt: "2026-01-01T00:00:00Z",
  finishedAt: "2026-01-01T00:10:00Z",
  result: {
    message: "Task executed successfully.",
  },
});
```

The client currently exposes read/create helpers for task runs (`getTaskRuns`, `getTaskRun`, `createTaskRun`).
