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

const response = await hs.monitoringSites.list({ page: 1, page_size: 50 });
if (response.ok) {
  console.log(response.data);
} else {
  console.error(response.message);
}
```

Use `host: ""` for same-origin requests. Applications that prefer dependency injection can instead call `HydroServer.initialize({ host })` and pass the returned instance explicitly.

### Tokens managed by your app

If your app already holds HydroServer access tokens, for example from a backend that signs users in through HydroServer, pass an `accessTokenProvider`. It's called before each request, so it should cache the token until shortly before it expires:

```ts
await createHydroServer({
  host: "https://playground.hydroserver.org",
  accessTokenProvider: async () => {
    const res = await fetch("/my-app/hydroserver-token/");
    return res.ok ? (await res.json()).access_token : null;
  },
  onUnauthorized: () => window.location.assign("/login/"),
});
```

A request rejected with a `401` is retried once with a token fetched again from the provider; if it's still rejected, the client calls `onUnauthorized` and emits `session:expired`. Your app handles sign-in and sign-out in this mode, and the option can't be combined with `oidc`. See the [TypeScript client how-to guide](https://github.com/hydroserver2/hydroserver/blob/main/apps/docs/docs/developing-and-contributing/how-to/using-the-typescript-client.md#tokens-managed-by-your-app) for the scopes the token needs and how to serve it safely.

### Account return destinations

When taking a user to a server-rendered account page, provide the in-app path
that the auth shell should return to. This controls its **Go back** link:

```ts
window.location.assign(hs.session.getAccountSignupUrl('/browse'))
window.location.assign(hs.session.getAccountProfileUrl('/settings'))
```

## Services

- Account: `session`, `user`
- Data management: `workspaces`, `monitoringSites`, `datastreams`, `methods`, `units`, `processingLevels`, `observedProperties`, `resultQualifiers`
- Orchestration: `dataConnections`, `tasks`, `monitoringTasks`, `dataProductTasks`, `ratingCurves`
- Files and QC: `monitoringSiteFileAttachments`, `qualityControlHistories`, `qualityControlSessions`, `qualityControlOperations`

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
import type { MonitoringSiteContract } from '@hydroserver/client'

type MonitoringSite = MonitoringSiteContract.DetailResponse['data']
```

`npm pack` and `npm publish` automatically build the client through `prepack`.
Run `npm test -- --run` and `npm run test:package` before publishing client
changes. The package check builds and packs the client, extracts it into an
isolated consumer directory, and type-checks its declarations with library
checking enabled across supported module resolution modes.
