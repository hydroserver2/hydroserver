# Architecture &amp; Software Stack

This document covers the technology choices, the reasoning behind them, the
system topology, and the invariants you should preserve when making changes.
For a "what the app does" walkthrough, see the [README](../README.md). For
the end-user perspective, see [USER_GUIDE.md](./USER_GUIDE.md).

## Stack at a glance

| Layer            | Technology                                   | Why this choice                                                                 |
|------------------|----------------------------------------------|---------------------------------------------------------------------------------|
| UI framework     | Vue 3 (Composition API, `<script setup>`)    | Same framework as `hydroserver-data-management-app`; lets HydroServer maintainers move between apps without re-learning the runtime. Composition API + `<script setup>` keeps components small and testable. |
| UI kit           | Vuetify 3 + MDI icons                        | Material Design, accessible primitives, theming, and a ready-made navigation drawer pattern. Cuts custom CSS to a minimum. |
| State            | Pinia (+ `pinia-plugin-persistedstate`)      | Pinia is the official Vue 3 store; tree-shakeable, fully typed, no boilerplate. The persistence plugin handles `localStorage` rehydration for workspace + UI prefs. |
| Routing          | vue-router 5                                 | Only three routes; vue-router is the standard.                                  |
| Charting         | Plotly.js (`plotly.js-dist`)                 | Multi-axis synchronized plotting, lasso + box selection, programmatic restyle, mature in the science community. ECharts and uPlot were prototyped; Plotly's mature selection model was the deciding factor. |
| QC engine        | `@uwrl/qc-utils`                             | Worker-parallelized typed-array kernels with a replayable history. Lives in a sibling repo (`qc-utils/`) so non-Vue consumers can reuse it. |
| Backend client   | `@hydroserver/client`                        | Generated typed REST client around the HydroServer Django + django-ninja API. Keeps endpoint shapes in sync with the backend. |
| Build / dev      | Vite 7                                       | Fast cold start, native ESM, first-class TypeScript + Vue SFC support. The dev server is also what serves the COOP/COEP headers `SharedArrayBuffer` needs. |
| Type system      | TypeScript 5 (strict)                        | Surfaces shape errors early; eliminates a class of regressions around `ObservationRecord` API drift. |
| Unit tests       | Vitest + Vue Test Utils (`jsdom`)            | Shares the Vite build pipeline, runs in-process, transparent ESM. |
| E2E tests        | Playwright (chromium + firefox)              | Cross-browser, headless-or-headed, intercepts network requests cleanly. WebKit excluded — see [QUALITY.md](./QUALITY.md). |
| Auth             | HydroServer session cookies + Google OAuth   | Same auth surface as the data-management app; no separate identity provider to operate. |
| Package manager  | npm                                          | Stays compatible with CI cache + the published `@uwrl/qc-utils` workflow.       |

### Database technology

**The QC App itself runs no database.** It is a static SPA. Persistent state
lives in three places, in increasing order of authority:

1. **In-memory typed arrays** — every loaded observation window is held in a
   pair of `Float64Array` (datetimes, ms epoch) + `Float32Array` (values),
   backed by a `SharedArrayBuffer` when COOP/COEP are on so worker kernels
   can scan the same memory without copying. Lives in `ObservationRecord`
   (qc-utils). Lost on reload — by design.
2. **`localStorage`** — workspace selection, drawer widths, persisted
   operator inputs (`pinia-plugin-persistedstate`). Per-browser, never
   sent to the backend. Use only for ephemeral UI prefs; **never** persist
   observation data here.
3. **HydroServer backend** — the system of record. The QC App reads
   observations and writes edited observations back via the
   `@hydroserver/client`'s `replace`-mode bulk POST. The backend stores
   everything in HydroServer's Postgres-compatible store, and is the
   place to look for archival, ACID, retention, and migration concerns.
   The QC App does not own any of that.

This split is deliberate: keeping the QC app stateless makes it trivial to
host (any object store + CDN works) and means a corrupted local cache can
always be recovered by a hard refresh.

## System context

```
                ┌──────────────────────────────────────────┐
                │  Operator's browser                      │
                │                                          │
                │  ┌────────────────────────────────────┐  │
                │  │ HydroServer QC App (this repo)     │  │
                │  │  Vue + Vuetify UI                  │  │
                │  │  Pinia stores  ·  Plotly chart     │  │
                │  │  ──────────────────────────────    │  │
                │  │  @uwrl/qc-utils                    │  │
                │  │    ObservationRecord (SAB)         │  │
                │  │    Worker pool (per-op kernels)    │  │
                │  │    History  ·  QC script I/O       │  │
                │  └─────────────┬──────────────────────┘  │
                │                │ REST (JSON)             │
                └────────────────┼─────────────────────────┘
                                 │
                                 ▼
                ┌──────────────────────────────────────────┐
                │  HydroServer backend                     │
                │   (VITE_APP_API_URL — e.g.               │
                │    playground.hydroserver.org)           │
                │                                          │
                │  Django + django-ninja  ·  Postgres      │
                │  Workspaces · Things · Datastreams       │
                │  Observations (bulk read / replace)      │
                │  Result qualifiers · Auth (AllAuth)      │
                └──────────────────────────────────────────┘
```

All QC computation runs in-browser. The backend never sees the intermediate
edit state — it only sees the final observations the operator chooses to
submit.

## Source layout

```
src/
├─ App.vue, main.ts             Entry point, plugin wiring (Vuetify, Pinia, router).
├─ pages/                       Top-level routed views (Home, Workspaces, Login).
├─ components/
│  ├─ Navigation/               NavigationRail, SelectDrawer, EditDrawer, PerformanceCalibration.
│  ├─ VisualizeData/            DataVisualization (Plotly host), data table, info card, filters.
│  ├─ FilterPoints/             One panel per filter op (ValueThreshold, GapFinder, Persistence, …).
│  ├─ EditData/                 One panel per edit op (FillGaps, ChangeValues, Interpolate, …)
│  │                            plus EditHistory + the operation metadata registry.
│  ├─ account/                  OAuth widget, login glue.
│  └─ base/                     Generic Vuetify wrappers (FullScreenLoader, Notifications).
├─ composables/
│  ├─ useDataSelection.ts       Bridges Plotly's selectedpoints into the Pinia store.
│  ├─ useFilterDispatch.ts      Shared "open panel → dispatch op → highlight result" flow.
│  ├─ useQcScript.ts            Save / load QC scripts (calls qc-utils' serializeHistory / applyScript).
│  ├─ useQcSubmission.ts        Submit the QC'd observations back to HydroServer (replace mode).
│  ├─ useResizable.ts           Generic drag-to-resize hook used by drawers + the plot.
│  └─ useBufferedNumber.ts      Debounced numeric input wrapper for filter panels.
├─ store/                       Pinia stores — see "State stores" below.
├─ utils/
│  ├─ plotting/                 Plotly integration (trace builders, event handlers, selection, staging).
│  ├─ dateMath.ts               Time-range arithmetic for presets ("1w", "1m", "All", …).
│  ├─ observations.ts           Observation fetch helpers (paged columnar fetch).
│  ├─ rules.ts                  Vuetify form validation rules.
│  └─ time.ts                   Time unit conversions.
├─ router/                      vue-router setup, auth + workspace guards.
├─ plugins/vuetify.ts           Vuetify theme + icon set.
├─ config/settings.ts           Runtime config from `VITE_APP_*` env vars.
├─ models/, types/              TypeScript models and ambient declarations.
└─ testHooks.ts                 `window.__vbwTestHooks` for Playwright (gated on VITE_APP_E2E_HOOKS).
```

## State stores (Pinia)

Each store owns a slice of UI / domain state. Every cross-store dependency
goes one direction.

| Store                 | Responsibility                                                        |
|-----------------------|-----------------------------------------------------------------------|
| `workspaces.ts`       | Workspace list, current selection (persisted).                        |
| `hydroserver.ts`      | The `@hydroserver/client` instance + session state.                   |
| `user.ts`             | Logged-in user, auth state, OAuth providers.                          |
| `observations.ts`     | Fetch + cache observation windows per datastream.                     |
| `dataVisualization.ts`| Selected datastream, plotted streams, QC datastream, selectedData.    |
| `plotly.ts`           | Plot ref, edit history, redraw, `suppressedEchoSelection` sentinel.    |
| `qualifiers.ts`       | Result qualifier codes per workspace.                                 |
| `userInterface.ts`    | Drawer state (Select/Edit), persisted prefs, current view.            |
| `operationParams.ts`  | Per-operation form inputs, persisted so they survive panel re-opens.  |
| `uiLayout.ts`         | Drawer widths, table heights — persisted UI geometry.                 |

The persisted stores use `pinia-plugin-persistedstate` with explicit
`storage: localStorage` and an explicit `paths` list. **Never** persist
ephemeral state (drawer open flags during a single session are fine; the
current plot ref or fetched observations are not — they belong in memory).

## Data flow: a QC edit

```
 ┌──────────────────────────┐
 │ User opens an op panel   │
 │ (e.g. ValueThreshold)    │
 └──────────────┬───────────┘
                ▼
 ┌──────────────────────────────────────┐
 │ Panel collects args                  │
 │ (e.g. { 'Greater than': 100 })       │
 └──────────────┬───────────────────────┘
                ▼
 ┌──────────────────────────────────────┐
 │ useFilterDispatch / useQcScript      │
 │   selectedSeries.data.dispatch(...)  │  ──►  qc-utils ObservationRecord
 └──────────────┬───────────────────────┘            · routes inline vs worker (calibration)
                │                                    · mutates typed arrays
                │                                    · appends HistoryItem
                ▼
 ┌──────────────────────────────────────┐
 │ plotly store: redraw()               │
 │   pushes new x / y into Plotly       │
 │   restyles selection / staging       │
 └──────────────────────────────────────┘
```

Invariants:

- **The UI never mutates typed arrays directly.** Every change goes through
  `ObservationRecord.dispatch` / `dispatchAction` / `dispatchFilter`. This
  is what makes the history replayable, the worker fast-path correct under
  SharedArrayBuffer, and the QC script export round-trip safe.
- **Selection is dispatch-driven.** When the user clicks or lassoes points,
  `useDataSelection` converts the Plotly event into a `SELECTION` dispatch,
  which appends a `HistoryItem`. Selection-consuming edits (Change Values,
  Interpolate, etc.) read from `history[length - 2].selected`.
- **`suppressedEchoSelection` exists for a reason.** Plotly emits
  `plotly_selected` events both for user gestures and for our programmatic
  `Plotly.restyle({ selectedpoints })` calls. The sentinel in `plotly.ts`
  drops the echo so we don't append a duplicate `SELECTION` entry.
- **The first plotted stream is the QC target.** The others are read-only
  context traces. Dispatch only ever runs against `selectedSeries.data`.

## Plotly integration

`src/utils/plotting/` is split by concern so each file has isolated mocks
in tests.

| File             | Concern                                                                |
|------------------|------------------------------------------------------------------------|
| `plotly.ts`      | Barrel + low-level trace builders, `setSelectedPoints`, `clearSelection`. |
| `events.ts`      | `plotly_click` / `plotly_relayout` / `mousemove` handlers.             |
| `relayout.ts`    | Debounced viewport recomputation, tick alignment.                      |
| `selected.ts`    | Translates Plotly selection events into a `SELECTION` dispatch.        |
| `staging.ts`     | Ghost-fill markers + drag-resizable stage shape (Add Points, Fill Gaps). |
| `interaction.ts` | High-level "user clicked a point" / "user dragged the stage" wiring.   |
| `operations.ts`  | Per-op redraw concerns (highlighting after a filter, fading after delete). |
| `zoom.ts`        | Synchronized multi-axis zoom + scroll-zoom handling.                   |
| `internal.ts`    | Shared private helpers (not exported through `plotly.ts`).             |

## qc-utils boundary

This app is the only in-tree consumer of `@uwrl/qc-utils`, but qc-utils
itself has zero Vue / Pinia / Plotly dependencies. The contract:

- The qc-app holds a `GraphSeries` per plotted datastream. The `data` field
  is an `ObservationRecord` from qc-utils.
- All editing happens via `series.data.dispatch(...)`. The app reads
  `dataX` / `dataY` only to hand them to Plotly via `redraw()`.
- Save / load uses `serializeHistory` / `parseScript` / `applyScript`. The
  app supplies the wall-clock window (begin/end of the current Plot range)
  on save and fetches the script's window on load.
- Performance routing (`shouldUseWorker`) is opt-in. The app calls
  `ensureCalibration()` on first idle so the first real op already has a
  decision. The `PerformanceCalibration` nav-rail entry exposes manual
  re-benchmark.

Side-stepping `dispatch` breaks undo / redo, breaks QC script export, and
silently breaks the worker fast-path. Don't.

## Routing and auth

vue-router 5, three routes (Home, Workspaces, Login). Two guards run on
every navigation:

- **`hasAuthGuard`** — redirects unauthenticated users to `/login` and
  remembers the intended destination.
- **`hasWorkspaceGuard`** — redirects users without a selected workspace
  to `/workspaces`.

The nav rail's "Edit" entry is gated behind a selected QC datastream and
runs the "unsaved edits" confirmation dialog before navigating away from
an in-progress QC session (see `NavigationRail.vue` + `useQcSubmission.ts`).

Auth itself is delegated to HydroServer's Django AllAuth setup; the app
keeps no credentials of its own. The browser holds a session cookie.

## Cross-origin isolation

COOP/COEP are on by default. `vite.config.ts` sets
`Cross-Origin-Opener-Policy: same-origin` and
`Cross-Origin-Embedder-Policy: require-corp` so `SharedArrayBuffer` is
available for the qc-utils worker pool. The trade-off is that any
cross-origin response without `Cross-Origin-Resource-Policy` gets blocked
— so older HydroServer deployments that don't yet serve CORP headers need
`VITE_APP_DISABLE_COOP=1` to drop the headers. When SAB is unavailable
the worker layer falls back to inline kernels, so the app keeps working
either way (just slower on large edits).

## See also

- [README](../README.md) — quick start, config, scripts
- [ONBOARDING.md](./ONBOARDING.md) — first-day setup checklist + doc gaps
- [DEPLOYMENT.md](./DEPLOYMENT.md) — infrastructure, operations, upgrades
- [API_REFERENCE.md](./API_REFERENCE.md) — store / composable / util surfaces, REST integration
- [PERFORMANCE.md](./PERFORMANCE.md) — performance characteristics and scaling
- [QUALITY.md](./QUALITY.md) — testing posture, code quality, tech debt
- [USER_GUIDE.md](./USER_GUIDE.md) — operator-facing feature walkthrough
