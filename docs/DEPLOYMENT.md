# Deployment, Publishing &amp; Operations

`@uwrl/qc-utils` is a library, not a service — "deployment" here means
the publishing pipeline and the day-to-day operations of releasing new
versions. It does not run as a server, it has no infrastructure to
operate, and it has no observability surface of its own.

## Shape of a release

```
        ┌────────────────┐    ┌──────────┐    ┌────────────────┐
git tag → │  CI (GH       │ →  │  npm run │ →  │ npmjs.com      │
v0.0.x   │  Actions)     │    │  pub     │    │ @uwrl/qc-utils │
        │  - type-check │    │ publish  │    │  (public)      │
        │  - coverage   │    │  --access │    └────────────────┘
        │  - lint       │    │  public  │            │
        │  - build      │    └──────────┘            ▼
        └────────────────┘                ┌────────────────────┐
                                          │ Consumers:         │
                                          │  - hydroserver-qc- │
                                          │    app             │
                                          │  - any browser /   │
                                          │    Node consumer   │
                                          └────────────────────┘
```

There is no static-asset deploy, no CDN, no container registry, and no
running service. The published artifact is the npm tarball, and the
"runtime" is whatever the consumer's bundler does with it.

## CI gates

`.github/workflows/ci.yml` runs on every push and PR to `main`:

1. `npx tsc --noEmit` — type-check.
2. `npm run coverage` — Vitest + v8 coverage at the 80% threshold.
3. `npm run lint` — ESLint.
4. `npm run build` — production build + `.d.ts` emission to `dist/`.

Concurrency is grouped by workflow + ref with `cancel-in-progress: true`.

Dependabot is enabled (`.github/dependabot.yml`); a
`dependabot-reviewer.yml` workflow auto-approves trivial bumps after
CI.

## Publishing a release

```bash
# 1. Make sure main is green and your local checkout is up to date
git checkout main
git pull
npm ci                      # clean install
npm run coverage            # match CI locally
npm run lint
npm run build               # rebuilds dist/ — published artifact

# 2. Bump the version (manual edit of package.json or npm version)
npm version <patch|minor|major>   # also creates a git tag

# 3. Push the tag
git push --follow-tags

# 4. Publish
npm run pub                 # npm publish --access public
```

`npm run pub` resolves to `npm publish --access public` (see
`package.json`). The `files` allowlist limits the tarball to `dist/`,
so source / tests / docs are not in the published artifact.

## What gets published

```
dist/
├─ index.js          ESM entry
├─ index.cjs         CJS shim (legacy consumers)
├─ types.d.ts        Type declarations (entry; tsconfig points here)
├─ *.d.ts            Per-module declarations
└─ <op>.worker-*.js  Inlined worker bundles
```

`package.json` exports:

```jsonc
{
  "main":   "./dist/index.cjs",
  "module": "./dist/index.js",
  "types":  "./dist/types.d.ts",
  "exports": {
    ".": { "require": "./dist/index.cjs", "import": "./dist/index.js" }
  }
}
```

A subpath import is **not** supported today — consumers depend on the
single entry. If you need a smaller bundle you can rely on the
consumer's tree-shaker; the cores and workers are sized so the unused
ones are dropped.

## Versioning

The project is pre-1.0. Treat the contract as:

- **Patch (`0.0.x → 0.0.y`)**: bug fixes, perf improvements, internal
  refactors that don't change the exported types.
- **Minor (`0.x.0 → 0.y.0`)**: new ops, additive type changes,
  intentional breaking changes (because pre-1.0). Consumers should
  read commit messages and bump deliberately.
- **Major**: reserved for 1.0 and beyond.

The qc-app pins via `^0.0.x` (caret on a `0.0.x` resolves only patch
bumps), so the integration is tightly coupled today. Both repos move
together. See [hydroserver-qc-app DEPLOYMENT.md](../../hydroserver-qc-app/docs/DEPLOYMENT.md#qc-utils-version-upgrades)
for the consumer-side upgrade flow.

## Running independently

`@uwrl/qc-utils` works in any modern browser context that exposes
`Float64Array` / `Float32Array` with `resize()` and (optionally)
`SharedArrayBuffer` with `grow()`. The realistic targets are:

- **Browser SPA** — the canonical case. COOP/COEP unlocks SAB; without
  them the worker layer falls back to inline. See "SharedArrayBuffer
  requirement" in [ARCHITECTURE.md](./ARCHITECTURE.md).
- **Web worker / service worker** — consumer wraps `ObservationRecord`
  inside a worker of its own. Nested workers work in modern browsers
  but spawn overhead compounds; calibration may decide inline anyway.
- **Node (newer LTS)** — the bare typed-array surface works; the
  `?worker&inline` Vite worker imports won't resolve in Node, so the
  worker fast-path is unavailable. `shouldUseWorker` returns
  `useWorker: false` and everything runs inline. Acceptable for
  scripting / CLI / test fixtures.
- **Pyodide** — same story as Node; Pyodide can drive
  `ObservationRecord` if you bundle the package and accept inline-only.

There is no "deploy qc-utils to production" step. The library lives
wherever the consumer's bundler put it.

## Observability

Library-level. The dispatcher writes a per-dispatch `execution`
record onto each `HistoryItem` (timing, worker/inline mode, dataset
shape at dispatch, selection size, status), so the consumer can
read it for in-process telemetry. There is no built-in remote
reporting, no Sentry / Datadog integration. The consumer is
responsible for any RUM-style observability.

The recommended hooks for a consumer that wants to observe:

```ts
record.dispatch(...)                       // wrap this call
// after it returns:
const last = record.history[record.history.length - 1]
const e = last.execution
console.log(last.method, e.durationMs, e.mode, e.status, e.datasetSize, e.selectionSize)
```

`onCalibrationChange(cb)` lets you observe (re-)benchmark events; the
calibration cache fires it on store, refresh, and `clearCalibration`.

## Upgrades and migrations

### Of `@uwrl/qc-utils` itself

The library is forward-only — old QC scripts must still replay on newer
versions. The contract is:

- **`QC_SCRIPT_VERSION` is bumped** when the wire format changes
  incompatibly. `parseScript` throws on mismatched versions. Today the
  format is at `"1"`.
- **Adding a new op** is a minor bump. Old scripts still replay.
- **Removing an op** is a breaking change. Old scripts that referenced
  the removed op replay with a per-op failure in
  `ApplyScriptReport.failed`, not an abort.
- **Renaming an op** is a breaking change without an alias — also use
  `applied/failed` semantics. Better to add the new name and accept
  the old one as a deprecated alias for one minor cycle.

### Of the calibration cache

`localStorage` key `qc-utils:calibration:v<n>` is versioned. Bump the
version constant in `calibration.ts` to invalidate the cache; existing
entries are left intact (no cleanup) but ignored on the next read.

### Of dependencies

- **Vite** is the build tool. Major Vite bumps may require config
  changes; smoke-test with `npm run build` and inspect `stats.html` for
  unexpected size regressions.
- **rxjs** is used minimally (`Subject` for calibration events). Major
  rxjs bumps rarely break us, but `npm run coverage` will surface
  anything that does.
- **`@vitest/web-worker`** is the worker test plugin. If worker tests
  start hanging, this is the first suspect.

## Day-2 operations

There are none. The library has no runtime to monitor. The operational
surface is:

- **CI green or red.** Watch via GitHub Actions.
- **npm publish succeeded.** Verify on <https://www.npmjs.com/package/@uwrl/qc-utils>.
- **Consumer caught up.** Bump `@uwrl/qc-utils` in the consumer's
  `package.json` once the release is live.
- **No alerts.** If a consumer reports a regression, the fix flows
  through the same CI → version-bump → publish loop.

## See also

- [README](../README.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [API_REFERENCE.md](./API_REFERENCE.md)
- [QUALITY.md](./QUALITY.md)
- [hydroserver-qc-app DEPLOYMENT.md](../../hydroserver-qc-app/docs/DEPLOYMENT.md)
  — consumer-side upgrade flow
