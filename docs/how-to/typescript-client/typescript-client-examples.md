# How to Manage Data with the TypeScript Client

The HydroServer TypeScript client is built for developers who want to create HydroServer frontends with TypeScript or JavaScript. It provides a browser-first API, typed models, and convenience helpers for common data management workflows.

This guide focuses on practical usage patterns you can apply in real applications.

## Install

```bash
npm install @hydroserver/client
```

## Initialize the client

Initialize the client once at app startup. The client uses session cookies for authentication.

```ts
import hs, { createHydroServer } from "@hydroserver/client";

await createHydroServer({ host: "https://playground.hydroserver.org" });
```

`createHydroServer` initializes the client and binds the default `hs` export to a shared, ready-to-use instance. Call it once at app startup (for example in `main.ts`) and then import `hs` anywhere you need to access the API.

## Alternative: HydroServer.initialize()

If you prefer to manage the instance yourself, call `HydroServer.initialize()` directly. This returns a client instance without relying on the shared `hs` proxy.

```ts
import { HydroServer } from "@hydroserver/client";

const client = await HydroServer.initialize({
  host: "https://playground.hydroserver.org",
});

const things = await client.things.listAllItems();
```

If your UI is served from the same domain as HydroServer, pass `host: ""` to use same-origin requests. For local development against a remote server, configure a dev proxy or CORS on the server to avoid browser CORS errors.

## Core collections

The client exposes the following core collections:

- workspaces
- things
- datastreams
- sensors
- units
- processingLevels
- observedProperties
- resultQualifiers
- orchestrationSystems
- dataConnections
- tasks

## Responses and errors

Most methods return an `ApiResponse` with `ok`, `data`, `status`, `message`, and optional `meta` fields.

```ts
const res = await hs.workspaces.list();
if (!res.ok) {
  console.error(res.message);
} else {
  console.log(res.data);
}
```

## Collections

All collection services support `list`, `listItems`, and `listAllItems`.

- `list` returns an `ApiResponse` containing the page.
- `listItems` returns just the data array (or `[]` on error).
- `listAllItems` fetches all pages.

### Example: Fetch all workspaces you belong to

```ts
const workspaces = await hs.workspaces.listAllItems({
  is_associated: true,
  expand_related: true,
});
```

### Example: Paginate and sort

```ts
const res = await hs.datastreams.list({
  page: 2,
  page_size: 50,
  order_by: ["name"],
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

await hs.session.logout();
```

## Workspaces

### Example: Update a workspace

```ts
const workspace = await hs.workspaces.getItem(workspaceId);
if (!workspace) {
  throw new Error("Workspace not found");
}

workspace.name = "Updated Workspace Name";
await hs.workspaces.update(workspace);
```

### Example: Manage collaborators

```ts
await hs.workspaces.addCollaborator(workspaceId, "user@example.com", roleId);
await hs.workspaces.updateCollaboratorRole(
  workspaceId,
  "user@example.com",
  roleId
);
await hs.workspaces.removeCollaborator(workspaceId, "user@example.com");
```

## Sites (Things)

### Example: Update site privacy

```ts
await hs.things.updatePrivacy(siteId, true);
```

### Example: Add a tag

```ts
await hs.things.createTag(siteId, { key: "region", value: "utah" });
```

## Datastreams

### Example: List datastreams for a site

```ts
const datastreams = await hs.datastreams.listAllItems({
  thing_id: [siteId],
});
```

### Example: Fetch observations

```ts
const res = await hs.datastreams.getObservations(datastreamId, {
  order_by: ["phenomenonTime"],
  page_size: 1000,
  format: "row",
  phenomenon_time_min: "2025-01-01T00:00:00Z",
  phenomenon_time_max: "2025-02-01T00:00:00Z",
});
```

### Example: Download a CSV

```ts
await hs.datastreams.downloadCsv(datastreamId);
```

## Orchestration systems

### Example: List orchestration systems in a workspace

```ts
const systems = await hs.orchestrationSystems.listAllItems({
  workspace_id: [workspaceId],
});
```

## Data connections

### Example: Create a data connection

```ts
import { DataConnection, Workspace } from "@hydroserver/client";

const dataConnection = new DataConnection();
dataConnection.name = "Daily CSV loader";
const workspace = new Workspace();
workspace.id = workspaceId;
dataConnection.workspace = workspace;
dataConnection.extractor.settings.sourceUri = "https://example.com/data.csv";

const res = await hs.dataConnections.create(dataConnection);
```

### Example: List data connections with details

```ts
const connections = await hs.dataConnections.listAllItems({
  workspace_id: [workspaceId],
  expand_related: true,
  order_by: ["name"],
});
```

## Tasks

### Example: Create a task

```ts
import { Task } from "@hydroserver/client";

const task = new Task();
task.name = "Daily load";
task.workspaceId = workspaceId;
task.dataConnectionId = dataConnectionId;
task.orchestrationSystemId = orchestrationSystemId;

const res = await hs.tasks.create(task);
```

### Example: Run a task and inspect status

```ts
await hs.tasks.runTask(taskId);

const tasks = await hs.tasks.listAllItems({
  workspace_id: [workspaceId],
  expand_related: true,
});

const statusText = hs.tasks.getStatusText(tasks[0]);
```
