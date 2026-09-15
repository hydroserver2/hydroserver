# HydroServer TypeScript Client

Typed browser client for HydroServer's authentication, data-management, orchestration, file-attachment, and quality-control APIs.

## Install

```bash
npm install @hydroserver/client
```

The client requires Node.js 20 or newer for development and packaging.

## Initialize

Initialize the shared client once before using its services:

```ts
import hs, { createHydroServer } from "@hydroserver/client";

await createHydroServer({ host: "https://playground.hydroserver.org" });

const response = await hs.things.list({ page: 1, page_size: 50 });
if (response.ok) {
  console.log(response.data);
} else {
  console.error(response.message);
}
```

Use `host: ""` for same-origin requests. Applications that prefer dependency injection can instead call `HydroServer.initialize({ host })` and pass the returned instance explicitly.

## Services

- Account: `session`, `user`
- Data management: `workspaces`, `things`, `datastreams`, `sensors`, `units`, `processingLevels`, `observedProperties`, `resultQualifiers`
- Orchestration: `dataConnections`, `tasks`, `monitoringTasks`, `dataProductTasks`, `ratingCurves`
- Files and QC: `thingFileAttachments`, `qualityControlHistories`, `qualityControlSessions`, `qualityControlOperations`

QC resources are nested. For example:

```ts
const histories = await hs.qualityControlHistories.listAllItems({
  managed_datastream_id: [managedDatastreamId],
});

const sessions = await hs.qualityControlSessions.listAllItems(historyId, {
  status: "committed",
  include_ancestors: true,
});

const operations = await hs.qualityControlOperations.listAllItems(
  historyId,
  sessionId
);
```

See the [TypeScript client how-to guide](https://github.com/hydroserver2/hydroserver/blob/main/apps/docs/docs/developing-and-contributing/how-to/using-the-typescript-client.md) for CRUD, observations, orchestration, attachments, and complete QC history examples. The [first app tutorial](https://github.com/hydroserver2/hydroserver/blob/main/apps/docs/docs/developing-and-contributing/tutorials/building-your-first-app.md) covers a minimal Vite setup.

## Generated API contracts

This package is published from the HydroServer monorepo. Its OpenAPI types and contracts are generated from the Django API schemas; do not edit files under `src/generated` manually.

`npm run gen` exports the current backend OpenAPI schemas from `django`,
regenerates the TypeScript types, and rebuilds the generated contract files.

`npm run check:contract` is the CI guard that fails when the committed client
artifacts drift from the latest backend API contract.

The build bundles the public API declarations using `rollup-plugin-dts`.
Schema types referenced by the public API are included inside the bundles; the
raw generated OpenAPI declaration files are not published separately.
The package exports select `index.d.ts` for ESM and `index.d.cts` for CommonJS,
including TypeScript's `node16`, `nodenext`, and `bundler` resolution modes.
Import public types from `@hydroserver/client`, for example:

```ts
import type { ThingContract } from '@hydroserver/client'

type ThingResponse = ThingContract.DetailResponse
```

`npm pack` and `npm publish` automatically build the client through `prepack`.
Run `npm test -- --run` and `npm run test:package` before publishing client
changes. The package check builds and packs the client, extracts it into an
isolated consumer directory, and type-checks its declarations with library
checking enabled across supported module resolution modes.
