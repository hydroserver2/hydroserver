# HydroServer Quality Control App

This web app facilitates QC/QA for time series observations stored in a HydroServer database instance. It features a multi-axis plot for visually overlaying datastreams and includes QC tools such as linear drift correction and interpolation.

[Documentation](https://hydroserver2.github.io/hydroserver/)

[Contributing](https://github.com/hydroserver2/hydroserver/blob/main/CONTRIBUTING.md)

[Issue Tracker](https://github.com/hydroserver2/hydroserver/issues)

[License](LICENSE)

## What it does

The app is the operator's view of HydroServer's QC pipeline:

1. **Browse** — pick a workspace, filter datastreams by site / observed property / processing level, and plot up to five at once on a synchronized multi-axis chart.
2. **QC one stream at a time** — the first plotted stream is the QC target. The other plotted traces are read-only context.
3. **Filter / edit / add** — every operation (Value Threshold, Find Gaps, Persistence, Interpolate, Drift Correction, Fill Gaps, Add Points, etc.) commits a `HistoryItem` to a replayable edit history backed by [`@uwrl/qc-utils`](https://www.npmjs.com/package/@uwrl/qc-utils).
4. **Save / load a QC History** — export the history as a JSON document, replay it on the same datastream a week later, or templatize across stations.
5. **Submit** — push the quality-controlled observations back to HydroServer in `replace` mode.

The heavy lifting (worker-parallelized typed-array kernels, calibration, history replay, save / load wire format) lives in `@uwrl/qc-utils`. This repo is the Vue / Vuetify / Pinia / Plotly UI plus the orchestration around it.

## Quick start

```bash
npm install
# Create .env.local with at least VITE_APP_API_URL (see Configuration below).
npm run dev                  # http://127.0.0.1:1203
```

**Use `127.0.0.1`, not `localhost`.** The HydroServer backend's CORS allowlist pins the IP literal, and the host name variant fails every API request silently. Vite's dev server is configured for `127.0.0.1:1203` to match.

### Configuration

`.env.local` (or `.env`) drives the runtime config. The keys the app reads:

| Var                              | Required | Purpose                                                                 |
|----------------------------------|----------|-------------------------------------------------------------------------|
| `VITE_APP_API_URL`               | yes      | Base URL of the HydroServer instance (e.g. `https://playground.hydroserver.org`). |
| `VITE_APP_VERSION`               | no       | Build-time version string surfaced in the about menu.                   |
| `VITE_APP_GOOGLE_OAUTH_ENABLED`  | no       | Show the Google sign-in button.                                         |
| `VITE_APP_DISABLE_ACCOUNT_CREATION` | no    | Hide the sign-up button (useful for invite-only deployments).           |
| `VITE_APP_DISABLE_COOP`          | no       | Drop the `Cross-Origin-Opener-Policy` + `Cross-Origin-Embedder-Policy` headers. Use only when the backend you're hitting doesn't serve `Cross-Origin-Resource-Policy` (older HydroServer deployments). The `qc-utils` worker layer falls back to inline kernels when SAB isn't available, so the app still works — just slower on large edits. |
| `VITE_APP_E2E_HOOKS`             | no       | Set to `1` to expose `window.__vbwTestHooks` for Playwright. CI sets this automatically. |

Cross-origin isolation is on by default (`vite.config.ts` sends `Cross-Origin-Opener-Policy: same-origin` + `Cross-Origin-Embedder-Policy: require-corp`) so `SharedArrayBuffer` is available to the qc-utils worker pool.

## Architecture at a glance

```
src/
├─ pages/                       Top-level routed views (Visualize, Edit, Submit, Auth).
├─ components/
│  ├─ Navigation/               NavigationRail, EditDrawer, SelectDrawer.
│  ├─ FilterPoints/             One panel per filter op (ValueThreshold, GapFinder, …).
│  ├─ EditData/                 One panel per edit op (FillGaps, ChangeValues, …) + EditHistory.
│  └─ VisualizeData/            DataVisualization, DataVisDatasetsTable, DatastreamInformationCard.
├─ composables/
│  ├─ useDataSelection.ts       The bridge between Plotly's selectedpoints and the Pinia store.
│  ├─ useFilterDispatch.ts      Shared "open panel → run op → highlight result" sequence.
│  └─ useQcHistory.ts            Wiring around qc-utils' serializeHistory / applyHistory.
├─ store/
│  ├─ plotly.ts                 Plot ref, edit history, redraw, suppressedEchoSelection sentinel.
│  ├─ dataVisualization.ts      Selected datastream, plotted streams, selectedData.
│  ├─ userInterface.ts          Drawer state, operator + filter inputs, persisted prefs.
│  └─ workspaces.ts             Workspace list + selected workspace (persisted).
├─ utils/plotting/
│  ├─ events.ts                 plotly_click / plotly_relayout / mousemove handlers.
│  ├─ relayout.ts               Debounced viewport recomputation, tick alignment.
│  ├─ selected.ts               handleSelected — translates Plotly selection into a SELECTION dispatch.
│  ├─ staging.ts                Ghost-fill markers + drag-resizable stage shape.
│  └─ plotly.ts                 Trace builders + low-level setSelectedPoints / clearSelection.
└─ router/                      vue-router 5 setup with workspace + auth guards.
```

The data flow for an edit is always: panel collects args → `useFilterDispatch` / `useQcHistory` calls `selectedSeries.data.dispatch(...)` (qc-utils) → qc-utils mutates typed arrays + appends a `HistoryItem` → `redraw()` pushes the new x / y into Plotly. The UI never touches the typed arrays directly.

## Working with `@uwrl/qc-utils` locally

When you're tweaking QC algorithms or worker kernels, link the sibling `qc-utils` checkout instead of bumping the npm version:

```bash
# qc-utils (terminal 1)
npm link
npm run dev          # vite watch — rebuilds dist/ on every save

# hydroserver-qc-app (terminal 2)
npm run link-qc-utils
npm run dev
```

Refresh the browser to pick up `qc-utils` changes — HMR doesn't propagate through linked packages. If the app surfaces stale type errors, run `npm run build` once in `qc-utils` to refresh `.d.ts`.

To unlink: `npm unlink @uwrl/qc-utils && npm install`.

## Testing

### Unit tests (Vitest)

```bash
npm test                      # watch mode
npm run coverage              # one shot + v8 coverage
```

Specs live next to source under `src/**/__tests__/`. Plotly is mocked at the module boundary; qc-utils workers use the inline mocks in `qc-utils/src/utils/plotting/__tests__/workerMocks.ts`.

### End-to-end tests (Playwright)

End-to-end specs cover the QC golden path: load a datastream, apply a filter, apply an edit, submit. Browser matrix: **chromium** and **firefox**. WebKit is intentionally excluded — `SharedArrayBuffer` + COOP / COEP behaviour differs in Safari and needs separate validation.

One-time setup:

```bash
npx playwright install chromium firefox
```

Run modes:

```bash
npm run test:e2e              # headed — opens a visible browser
npm run test:e2e:ci           # headless — CI mode, also fast for local
npm run test:e2e:live         # against playground.hydroserver.org (requires .env.local)
```

The Playwright `webServer` config auto-starts the Vite dev server at `http://127.0.0.1:1203` and reuses an existing one outside CI. The dev server is what serves the COOP / COEP headers `SharedArrayBuffer` needs — running e2e against a static `file://` build won't work.

The mocked specs (everything except `qc-golden-path.spec.ts`) intercept HydroServer routes via `page.route()` and serve fixture JSON, so most runs need no backend. The live `qc-golden-path` spec talks to `playground.hydroserver.org` and reads credentials from `.env.local`.

E2E specs live in `e2e/` (separate from the Vitest unit specs under `src/**/__tests__/`).

## Funding and Acknowledgements

Funding for this project was provided by the National Oceanic & Atmospheric Administration (NOAA), awarded to the Cooperative Institute for Research to Operations in Hydrology (CIROH) through the NOAA Cooperative Agreement with The University of Alabama (NA22NWS4320003). Utah State University is a founding member of CIROH and receives funding under subaward from the University of Alabama. Additional funding and support have been provided by the State of Utah Division of Water Rights, the World Meorological Organization, and the Utah Water Research laboratory at Utah State University.
