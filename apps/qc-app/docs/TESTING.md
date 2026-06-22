# Testing

How to run, write, and debug tests in `hydroserver-qc-app`.

For _what is and isn't covered_ (and the rationale behind the
exclusion list), see [QUALITY.md](./QUALITY.md). This document is
the operator's manual; QUALITY.md is the policy.

---

## Test layers

| Layer      | Runner                          | Where                        | Count    |
| ---------- | ------------------------------- | ---------------------------- | -------- |
| Unit       | Vitest                          | `src/**/__tests__/*.spec.ts` | 24 files |
| End-to-end | Playwright (Chromium + Firefox) | `e2e/*.spec.ts`              | 22 files |

There is no separate "integration" tier — component tests live in the
unit tier and mount real Vue components with the Vue Test Utils
`mount()` helper, mocking only the store boundary.

---

## Running tests

```bash
# Unit, watch mode (interactive)
npm test

# Unit, one-shot with v8 coverage report
npm run coverage

# E2E, one-shot headless on Chromium + Firefox
npm run e2e

# E2E, Playwright UI mode (recommended interactive flow)
npm run e2e -- --ui

# E2E against a live HydroServer through the Data Management same-origin entrypoint
npm run e2e:live

# Type-check the whole app (no emit)
npx vue-tsc --noEmit
```

`npm run coverage` is what CI runs and what gates merges (see
[CI](#ci)).

### Running a single file or test

```bash
# Unit — file or pattern
npx vitest run src/utils/plotting/__tests__/options.spec.ts
npx vitest run -t "createPlotlyOption"

# E2E — file, project, repeat
npx playwright test tooltip-threshold.spec.ts
npx playwright test --project=firefox --workers=1 --headed
npx playwright test history.spec.ts --repeat-each=5 --retries=0
```

For interactive debugging of a Playwright spec, prefer `--ui` over
`--headed` (see [E2E pitfalls](#e2e-pitfalls)).

---

## Unit tests

### Runner config

Vitest is configured in [`vite.config.ts`](../vite.config.ts) under
the `test` key — there is no separate `vitest.config.ts`. The
notable knobs:

- `environment: 'jsdom'` globally; `src/components/**` matches
  `jsdom` again via `environmentMatchGlobs` for symmetry.
- `setupFiles: ['@vitest/web-worker', './src/utils/test/setup.ts']`
  — the worker plugin lets `?worker&inline` imports resolve in
  Vitest; `setup.ts` stubs `HTMLCanvasElement.prototype.getContext`
  because jsdom doesn't implement it and Vuetify's mount cycle
  spams "Not implemented" warnings without the stub.
- `server.deps.inline: ['vuetify']` — Vuetify ships ESM that
  Vitest's default externalization mishandles; inlining lets it
  load.

### Test scaffolding

Live in `src/utils/test/`:

- `pinia.ts` — `createTestPinia()` creates a fresh Pinia and calls
  `setActivePinia()`. No `pinia-plugin-persistedstate` is wired so
  unit tests don't read or write `localStorage`.
- `vuetify.ts` — `createTestVuetify()` returns a default Vuetify
  instance for `mount()` plugin lists.
- `setup.ts` — the canvas stub described above.

Use them in component specs:

```ts
import { mount } from '@vue/test-utils'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

beforeEach(() => createTestPinia())

const wrapper = mount(MyComponent, {
  global: { plugins: [createTestVuetify()] },
})
```

### Conventions

These patterns recur across every spec in the project. New specs
should follow them.

1. **Mock the store boundary, not the internals.** Specs `vi.mock()`
   `@/store/<name>` and `@/composables/<name>` and return plain
   refs that the spec controls. The component under test runs its
   real reactivity through the mocked store proxy. See
   `src/components/EditData/__tests__/EditHistory.spec.ts` for the
   canonical example.

2. **Refs as state vehicles.** Test-controlled mock state goes
   through `ref()`s declared at module top-level. `beforeEach`
   resets them (`isUpdating.value = false`, etc.). This keeps mock
   factories pure (idempotent on re-evaluation) and lets a single
   spec poke state mid-test.

3. **Hoisted Plotly mocks.** Files that import `plotly.js-dist`
   transitively must declare the Plotly mock with `vi.hoisted()` so
   the mock is registered before the transitive import. See
   `src/utils/plotting/__tests__/relayout.spec.ts` for the pattern.

4. **`storeToRefs` mocks must include every ref the production code
   touches.** A missing ref throws `Cannot read properties of
undefined (reading 'value')` from inside a `setTimeout` (the
   relayout debounce), which surfaces as an unhandled rejection
   plus an unrelated assertion failure. When the store grows a new
   ref read by `handleRelayout`, the relayout spec mock needs the
   ref too. Same rule for `tooltipsMode`, `tooltipsMaxDataPoints`,
   `areTooltipsEnabled`.

5. **Reset between specs.** Tests that mutate shared state
   (`beginDate`, `qcDatastream`, `tooltipsMode`, the `applications`
   array used by qualifier-band tests) should reset in `beforeEach`
   via a `resetStoreState` helper. Drift across describe blocks is
   the most common cause of order-dependent failures.

### Coverage thresholds

Configured in [`vite.config.ts:130-140`](../vite.config.ts). The
gate is:

- Lines / statements / functions: **80%**
- Branches: **78%** (sits two points lower because a handful of
  branches in `options.ts`'s qualifier-band path and `selected.ts`'s
  relayout-echo path require Plotly-DOM fixture setup that isn't
  worth the marginal signal)

The exclusion list (`coverage.exclude`) is the longest single bit
of config in the file. Each entry is a deliberate scope decision —
read the inline comments before adding to it. The current shape:

- **Untested stores** (`observations`, `hydroserver`, `user`) are
  excluded because they're thin REST wrappers; they're exercised
  indirectly through E2E.
- **Vuetify-shell SFCs** (most of `components/EditData/`,
  `FilterPoints/`, `Navigation/`, the bulk of `VisualizeData/`)
  are excluded because mocking the v-component surface to mount
  them in jsdom costs more than the coverage delta is worth.
  Three SFCs (`EditHistory.vue`, `DataTable.vue`,
  `DatastreamFilters.vue`) are unit-tested as exemplars.
- **DOM-staging seams** (`events.ts`, `interaction.ts`,
  `operations.ts`, `staging.ts`) are excluded because their work is
  mostly `Plotly.restyle` / `Plotly.relayout` calls + drag-gesture
  wiring that resists meaningful unit testing.
- **Barrels and setup** (`main.ts`, `plotly.ts` re-export barrel,
  `router/`, `plugins/`, `types/`, `config/`, `*.d.ts`).

When you add a new file that should be tested but isn't yet,
**do not add it to the exclude list to keep coverage green** —
add a test or fail the build.

### When coverage fails

The CI gate prints uncovered line numbers per file. Common causes:

1. **A new branch introduced in production code.** Find the
   uncovered branch in the `Uncovered Line #s` column of the
   coverage report; add a targeted test that exercises the
   missing path. Helpers in `options.ts` (`findGapIndices`,
   `insertGapBreaks`) and `selected.ts`'s echo-suppression paths
   are good examples of how thin a branch test can be.
2. **A new file that should have a test.** Add a `__tests__/`
   sibling and write the spec rather than excluding the file.
3. **An exclude entry that's now wrong.** A file moved or grew
   coverage organically and no longer needs to be excluded.

---

## E2E tests

### Runner config

[`playwright.config.ts`](../playwright.config.ts) sets the QC app profile:

- `testDir: './e2e'`
- `fullyParallel: true` with `workers: process.env.CI ? 1 : 2`.
  The local default of 2 (instead of the Playwright default ~50%
  of cores) is **deliberate**: more workers overwhelm the shared
  Vite dev server and starve Firefox of CPU during boot — 12 of 24
  specs used to time out on `waitForSelection` before this cap.
- `retries: process.env.CI ? 2 : 1` — local runs allow one retry to
  swallow the occasional dev-server cold-start flake.
- `projects: chromium, firefox` only. WebKit is **excluded on
  purpose**: `SharedArrayBuffer` + COOP/COEP behavior diverges in
  Safari and would need its own validation pass.
- `baseURL: http://127.0.0.1:5173` — **never `localhost`**. The
  backend (`playground.hydroserver.org`) CORS-allowlists
  the `127.0.0.1` origins only; using `localhost` makes API requests fail
  with `net::ERR_FAILED` and the app never mounts.
- `webServer.command: npm run dev` with
  `env: { VITE_APP_E2E_HOOKS: '1' }`. The env var arms test hooks
  (see [Test hooks](#test-hooks)).

### Support layout

```
e2e/
├── support/
│   ├── app.ts        — flow helpers (gotoHome, setupEditView, openOp, waitForSelection)
│   ├── fixtures.ts   — workspace / datastream / observation fixtures
│   ├── mocks.ts      — page.route() handlers that stand in for HydroServer
│   └── ops.ts        — op-specific preambles (selectAllPoints, expectHistoryContains)
└── *.spec.ts         — one file per feature
```

### How a spec is structured

```ts
test.describe('edit: delete points', () => {
  test.beforeEach(async ({ page }) => {
    await installMocks(page) // stub HydroServer routes
    await setupEditView(page) // boot → plot → switch to edit view
    await selectAllPoints(page) // seed a selection via the panel UI
  })

  test('dispatches DELETE_POINTS for the current selection', async ({
    page,
  }) => {
    await openOp(page, 'deletePoints')
    await page.getByRole('button', { name: /^delete$/i }).click()
    await expectHistoryContains(page, 'Delete Points')
  })
})
```

Everything except `qc-golden-path.spec.ts` happens against the mocked
backend. The live golden-path spec is gated by `E2E_LIVE=1`, expects both
frontends to be running, and enters QC through the Data Management
same-origin entrypoint.

### Mocks

`installMocks(page, options?)` in `support/mocks.ts` registers a
single `page.route('**/api/**')` handler that pattern-matches on
the request path and returns fixture JSON. The shape mirrors
HydroServer's real responses (paginated, `X-Total-Pages` headers,
CORS echoed origin).

Per-spec overrides go through `options`:

```ts
await installMocks(page, {
  observations: { phenomenonTime: [...], result: [...] },
  submissions: collectedSubmissions,   // accumulates bulk POSTs for assertion
  authenticated: false,                 // simulate signed-out
})
```

### Fixtures: "now"-anchored timestamps

`support/fixtures.ts` exports a `FIXTURE_OBS_START_MS` anchored to
`Date.now()` at module load (currently 120 observations × 15-minute
spacing ending at "now"). The datastream's `phenomenonBeginTime` /
`phenomenonEndTime` and the default `buildObservations()` series
derive from this anchor.

Specs that build custom observation series (gap fixtures, plateau
fixtures, etc.) **must** import `FIXTURE_OBS_START_MS` and derive
their timestamps from it:

```ts
import { FIXTURE_OBS_START_MS } from './support/fixtures'

function observationsWithGap() {
  const startMs = FIXTURE_OBS_START_MS
  // …
}
```

### Test hooks

`src/testHooks.ts` registers `window.__vbwTestHooks` when
`import.meta.env.DEV` or `VITE_APP_E2E_HOOKS` is set. Today it
exposes one helper:

- `waitForSelectedData(minLength, timeoutMs)` — resolves when the
  Pinia store's `selectedData` has at least `minLength` entries.
  Used by `support/app.ts#waitForSelection`.

The hook is opt-in via env var so production builds never ship it.
Add new hooks here when a deterministic store-level signal is
faster / more reliable than a DOM probe.

### E2E pitfalls

These are the failure modes the suite has actually hit; cataloguing
them so the next contributor doesn't rediscover them.

1. **Use Enter on focused inputs, not `fill(...).click(button)`.**
   Vuetify's `v-text-field` debounces `update:modelValue` ever so
   slightly; Playwright on Firefox can fire the Apply / Add-filter
   click before the model commits, and the button's
   `:disabled="isUpdating || !value"` guard silently swallows the
   click. The fields' own `@keyup.enter` handlers dispatch in one
   event, removing the race:

   ```ts
   const value = page.getByLabel('Value')
   await value.fill('1')
   await value.press('Enter')
   ```

   `selectAllPoints`, `history.spec.ts`'s Change-Values preamble,
   and the tooltip-threshold spec already follow this pattern.

2. **The dev-server URL must be `127.0.0.1`, not `localhost`.**
   Configured in `playwright.config.ts` and `vite.config.ts`. If a
   spec navigates to `localhost` directly, the backend's
   CORS rejection cascades into `createHydroServer()` rejecting
   and the app never mounts. The mocked specs are immune (no
   real backend traffic) but live specs would fail invisibly.

3. **The mode menu doesn't auto-close on item click.** Vuetify's
   `v-menu` with `close-on-content-click="false"` (used for the
   data-points mode menu so the threshold form stays open during
   edits) leaves the menu open after picking a mode. Helpers like
   `pickMode` press Escape after the click and assert the menu's
   gone:

   ```ts
   await page.getByTestId('tooltips-mode-btn').click()
   await page.getByTestId(`tooltips-mode-${mode}`).click()
   await page.keyboard.press('Escape')
   await expect(page.getByTestId('tooltips-mode-menu')).toHaveCount(0)
   ```

4. **Browser windows steal focus.** Headed Vuetify components
   sometimes change behavior when the test window is not the
   foreground OS window. If a previously-green spec started
   failing only after you alt-tabbed, that's why.

### Debugging a failure

Playwright's HTML report (`playwright-report/index.html`) opens
automatically after a local run. Per-failure trace zips
(`test-results/<name>/trace.zip`) can be replayed with
`npx playwright show-trace <path>` — they include screenshots, DOM
snapshots, console logs, and network traffic at every step. This
is the single most useful debugging tool the suite has.

For a flaky spec specifically, the recipe is:

```bash
npx playwright test path/to/spec.ts --repeat-each=5 --retries=0
```

5 repeats × 2 browsers is usually enough to surface a flake; the
fix often follows the Enter-on-input or wait-for-stable-state
patterns above.

---

## CI

`.github/workflows/ci.yml` runs on every push and on every PR
targeting `main`. The job:

1. `npx vue-tsc --noEmit` — type-check.
2. `npm run coverage` — Vitest with the 80%/78% gates above.
3. `npm run build` — Vite production build.

---

## Adding new tests

### A new unit spec for a store / composable / utility

1. Create `<module>/__tests__/<module>.spec.ts`.
2. Import `createTestPinia` if the module touches Pinia; call
   `setActivePinia(createPinia())` (or `createTestPinia()`) in
   `beforeEach`.
3. Mock collaborator stores with `vi.mock(...)` and ref-backed
   fakes — see `selected.spec.ts` for a representative shape.
4. Run `npx vitest run <file>` until green; run
   `npm run coverage` once to verify the gate still passes.

### A new component spec

1. Same layout under `src/components/<Group>/__tests__/`.
2. `mount()` the component with
   `global: { plugins: [createTestVuetify()] }`.
3. Mock `@/store/*` and `@/composables/*` imports with refs you
   control from the spec — never import the real stores in a
   component test.
4. If the component imports `@uwrl/qc-utils`, mock the enum
   constants it uses (see `EditHistory.spec.ts` line 28-77 for
   the canonical shape).

### A new E2E spec

1. Create `e2e/<feature>.spec.ts`.
2. `import { installMocks } from './support/mocks'`,
   `import { setupEditView, openOp, waitForSelection } from './support/app'`,
   `import { selectAllPoints, expectHistoryContains } from './support/ops'`.
3. Structure: `beforeEach` → install mocks → boot UI → seed
   selection. One test per feature; `expect`s on observable UI
   state (`history-item-*` testid, `selectedData` via
   `waitForSelection`).
4. If you need a custom observation series, import
   `FIXTURE_OBS_START_MS` from `support/fixtures` and anchor your
   timestamps to it.
5. Run `npx playwright test <file>` on both projects:
   `--project=chromium` then `--project=firefox` (or both).

### A new test hook

1. Add the implementation in `src/testHooks.ts` under the
   `installTestHooks()` function — same registration pattern as
   `waitForSelectedData`.
2. Update the `Window['__vbwTestHooks']` interface in
   `e2e/support/app.ts` so spec callers get type-checking.
3. Hooks ship only when `import.meta.env.DEV` or
   `VITE_APP_E2E_HOOKS` is set — production builds never expose
   them.

---

## Maintenance checklist

When a Vuetify upgrade lands:

- Re-run the full unit suite; component specs that mock Vuetify
  internals (rare in this repo) may break.
- Re-run E2E on both projects; testid selectors may need updates
  if Vuetify reshuffles DOM internals.

When a `qc-utils` upgrade lands:

- Re-run unit specs that mock `@uwrl/qc-utils` enums — the
  canonical sites are `EditHistory.spec.ts` and any spec under
  `src/utils/plotting/__tests__/` that imports the enums.
- If a new `HistoryItem` field is added, the qc-app's `EditHistory`
  rendering may need an update; the spec coverage will catch
  that.

When a new Pinia store ref is read by `handleRelayout` or any
debounced path:

- Add it to `vi.mock('@/store/plotly')` in
  `src/utils/plotting/__tests__/relayout.spec.ts` and to
  `resetStoreState`. Missing refs throw inside a `setTimeout`
  and produce confusing unhandled-rejection failures.

When a Playwright spec starts flaking:

- Check the trace.zip first — it almost always shows the cause.
- If it's `waitForSelection` timing out, the suspect is a
  `fill('...').click(button)` pattern; switch to
  `field.press('Enter')`.
- If it's a button click that "didn't fire," the suspect is the
  `:disabled="isUpdating"` guard; wait for `isUpdating` to
  clear, or use the field's `@keyup.enter` handler.

When coverage drops below threshold after a code change:

- Add targeted tests for the new branches; do **not** lower the
  threshold or grow the exclude list to make the gate pass.
- The "Uncovered Line #s" column of the coverage report points
  directly at what's missing.

---

## See also

- [QUALITY.md](./QUALITY.md) — what is covered, what isn't, and why
- [ONBOARDING.md](./ONBOARDING.md) — the wider learning path
- [`vite.config.ts`](../vite.config.ts) — source of truth on
  Vitest config and coverage policy
- [`playwright.config.ts`](../playwright.config.ts) — source of
  truth on Playwright config
