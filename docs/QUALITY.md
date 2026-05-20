# Codebase Quality &amp; Maintainability

What a new team would need to know about the shape of this codebase
before making changes: readability standards, test coverage in concrete
numbers, and the technical debt that is real and worth surfacing rather
than discovering.

## Code style and readability

- **TypeScript 5, strict mode**, type-checked in CI with `vue-tsc --noEmit`.
- **Vue 3 Composition API** with `<script setup>`. Options API is not used.
- **`<script setup>`** components keep template / script / style colocated
  in single-file components; the template is the public surface, the
  script is implementation.
- **Pinia stores** define one slice of state each. Cross-store imports
  go one direction.
- **Comments only when they explain the non-obvious *why*.** "No band-
  aid solutions; do things the right way" is the standing rule. Inline
  comments are concentrated on the few invariants that resist being
  read off the code (e.g. the `suppressedEchoSelection` sentinel in
  `plotly.ts`, the `<` vs `<=` fix in `observations.ts`, the in-place
  clear in `useQcSubmission.ts`).
- **Prettier** for formatting (`.prettierrc`). No ESLint config in the
  qc-app repo today — lint is run on the qc-utils sibling but not here.
  This is a known gap (see "Tech debt" below).

## Test coverage

CI gate is **Vitest with v8 coverage, ≥80% lines / statements / functions
and ≥78% branches** (see `vite.config.ts`). The branches threshold sits
two points below the rest because a few uncovered branches in the
qualifier-band path of `options.ts` and the relayout-echo path of
`selected.ts` require heavy Plotly-DOM fixture setup for marginal
signal.

### What is covered

- Every Pinia store under `src/store/` that participates in coverage
  (see `vite.config.ts` excludes for the holdouts).
- All composables under `src/composables/__tests__/`.
- The plotting utility layer: `events`, `selected`, `zoom`, `internal`,
  `options`, `operations`, `interaction`.
- Three substantial SFCs under `src/components/`: `EditHistory.vue`,
  `DataTable.vue`, `DatastreamFilters.vue`.

### What is intentionally excluded from coverage

The blanket coverage excludes are listed inline in `vite.config.ts:74-128`
with rationale. The high-level groups:

| Group                                                  | Rationale                                                                |
|--------------------------------------------------------|--------------------------------------------------------------------------|
| `store/observations.ts`, `store/hydroserver.ts`, `store/user.ts` | Thin REST wrappers; tested via integration / E2E.                |
| Most `components/EditData/*.vue`, all `components/FilterPoints/*.vue`, all `components/Navigation/*.vue` | One operation panel per file — heavily Vuetify-driven; mocking the v-component surface costs more than the marginal coverage. Three SFCs are unit-tested as exemplars. |
| `components/VisualizeData/*.vue` (most), `pages/**`, `account/**`, `base/**` | Same Vuetify-shell rationale.                                  |
| `utils/plotting/events.ts`, `interaction.ts`, `operations.ts`, `staging.ts` | DOM-staging / Plotly relayout seams that resist meaningful unit testing. |
| `plugins/**`, `router/**`, `types/**`, `config/**`, `main.ts`, `*.d.ts` | Setup / declaration files with no logic.                       |

### E2E

Playwright specs in `e2e/`, run on **chromium and firefox only**.
WebKit is intentionally excluded — `SharedArrayBuffer` + COOP/COEP
behavior differs in Safari and needs separate validation.

Mocked specs intercept HydroServer routes via `page.route()`. The single
live spec `qc-golden-path.spec.ts` talks to `playground.hydroserver.org`
and reads credentials from `.env.local` — run with
`npm run test:e2e:live`.

### Manual / unmodeled testing

- Visual regression: not automated. UI changes are smoke-tested in the
  preview server (see [ONBOARDING.md](./ONBOARDING.md)).
- Performance regression: not automated. The calibration layer is
  measured per-device, and there is no historical perf benchmark in CI.

## Areas of technical debt

These are real, named, worth flagging up front. Not exhaustive — but
the items most likely to bite a new team in the first three months.

### 1. Result-qualifier submit path is partial

`store/qualifiers.ts` and `components/EditData/QualifyingComments.vue`
collect qualifier codes per selection, but
`composables/useQcSubmission.ts:42` only serializes
`['phenomenonTime', 'result']` on the bulk POST. The row format would
carry qualifiers, but it times out on >35k-point fetches today (see
`src/utils/observations.ts:24`). Resolution is blocked on the
HydroServer API team either making the columnar response carry
qualifiers via opt-in (`include=resultQualifierCodes`) or speeding up
the row mode. Tracked inline as a TODO.

### 2. No ESLint config

`prettier` formats but there is no lint pass. qc-utils has eslint; the
QC App does not. Adding one is straightforward — typescript-eslint +
vue-eslint-config-typescript — and would catch a class of issues that
slip through type-check today (unused vars, floating promises, etc).

### 3. Three large SFCs not yet unit-tested

`DataVisualization.vue`, `PlottedDatastreams.vue`, and `FilterPanel.vue`
are the three highest-complexity SFCs without unit tests. They are
exercised by E2E specs but lack the per-branch coverage the rest of the
project has.

### 4. Pinia store JSDoc is uneven

Some stores (`dataVisualization`, `plotly`) carry rich per-ref
docstrings; others (`uiLayout`, `operationParams`) carry almost none.
The store *behavior* is consistent, but a new contributor reading them
will get an asymmetric experience.

### 5. The plotting layer narrative

Each file under `src/utils/plotting/` is short and single-purpose,
but the composition into a redraw is implicit. The rationale for the
current split lives in commit history rather than a written design
doc. Tracing a single op end-to-end (panel → dispatch → restyle) is
the fastest way to learn the layer.

### 6. Documentation gaps

Listed in [ONBOARDING.md "Documentation gaps a new team will hit"](./ONBOARDING.md#documentation-gaps-a-new-team-will-hit).
Highlights:

- No formal API reference per-Pinia-store before this docs folder existed.
- No diagram of the auth flow.
- No customer-facing help site; the user guide lives in this repo.

### 7. Some persistence keys lack version handling

`workspaces`, `userInterface`, `uiLayout`, and `operationParams` are
persisted to `localStorage` without an explicit version key on the
persisted slice. If we ever need to break the shape, we'll have to
either prefix the key or do a one-time blow-away — the patch is small
but it is technical debt today. `qc-utils:calibration:v1` is the
template to copy.

### 8. The `apiMethods` re-export in qc-utils

`@uwrl/qc-utils` re-exports a HydroServer REST client (`api`,
`apiMethods`, interceptors) and a `Snackbar` helper for legacy reasons.
The QC App uses `@hydroserver/client` for the REST calls and
`Snackbar` from qc-utils — the qc-utils `api` is not consumed by the
app. Cleaning this up means a coordinated release of both packages.

### 9. `package.json` carries a transitive `npm` dependency

`"npm": "^11.8.0"` is listed under `dependencies`. This is an oddity —
npm is the package manager, not an app dependency. It's harmless but
should be removed during the next dependency sweep.

### 10. The demo deployment workflow inlines `.env` generation

`hydroserver_qc_app_demo_deployment.yaml` writes `.env` with a heredoc
that's missing the closing `EOF` line and only includes two of the
documented env keys. This currently works because `VITE_APP_API_URL`
is sourced from `PROXY_BASE_URL`, but it diverges from the documented
config surface. Worth normalizing during the next deploy-workflow
refresh.

## Dependency management

- **Dependabot** is enabled (`.github/dependabot.yml`); a separate
  `dependabot-reviewer.yml` workflow auto-merges trivial bumps after CI.
- **Major-bump audits** are run manually with `npm run up` (taze --major).
- **Vite, Vue, Vuetify, Plotly, qc-utils** are the five upgrade vectors
  that demand a manual smoke test. The rest are routine.

## Where the code is solid

To balance the debt list:

- **The qc-utils boundary is clean.** Side-stepping `dispatch` would be
  the easy mistake, and the code consistently doesn't.
- **The Pinia store split is principled.** Each store owns a slice
  with explicit one-way dependencies.
- **The Plotly integration is decomposed by concern.** Each file is
  short, named, and tested where testable.
- **The QC script format is versioned**, replayable, and stable on
  disk — this is the durability story you want.
- **CI is fast and gates the right things** (type-check, coverage,
  build).

## See also

- [TESTING.md](./TESTING.md) — how to run, write, and debug tests
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [ONBOARDING.md](./ONBOARDING.md) — documentation gaps and learning path
- [PERFORMANCE.md](./PERFORMANCE.md) — performance characteristics
- `vite.config.ts` — the source of truth on coverage thresholds + excludes
