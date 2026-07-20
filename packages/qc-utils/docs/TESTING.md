# Testing

How to run, write, and debug tests in `@uwrl/qc-utils`, plus the
maintenance traps specific to a worker-heavy library.

For *what is and isn't covered* (and the rationale behind the
exclusion list), see [QUALITY.md](./QUALITY.md). This document is
the operator's manual; QUALITY.md is the policy.

---

## Test layers

The library has no UI and no DOM-bound surface outside the
`Snackbar` helper, so there's a single layer — Vitest unit specs —
but the suite is split by *what shape of system under test*:

| Spec file                              | Surface covered                                                  |
|----------------------------------------|------------------------------------------------------------------|
| `operation-cores.spec.ts`              | Every inline kernel in `operation-cores.ts`; edge cases (empty, single-point, NaN). |
| `workers.spec.ts`                      | Every `*.worker.ts` handler — wiring smoke + the two inline-only workers. |
| `observation-record.spec.ts`           | Public dispatch surface, undo / redo / reload, history shape.    |
| `observation-record-paths.spec.ts`     | Inline vs worker routing decisions; both success and failure paths. |
| `history.spec.ts`                       | `serializeHistory` / `parseHistory` / `applyHistory` round-trip, per-op failures, timestamp persistence. |
| `calibration.spec.ts`                  | Benchmark math, fallback profile, decision predictions.          |
| `calibrated-dispatch.spec.ts`          | Benchmark-driven end-to-end check that every calibrated op routes inline below its predicted crossover and to a worker above it. Runs the benchmark once in `beforeAll`, then binary-searches the crossover per op. |
| `format.spec.ts`, `ellapsed-time.spec.ts`, `observations.spec.ts`, `notifications.spec.ts` | Standalone helper modules.            |

11 spec files total, ~230 tests.

---

## Running tests

```bash
# One-shot, all specs
npm test

# One-shot with v8 coverage report (CI runs this)
npm run coverage

# Type-check
npx tsc --noEmit

# Lint (also gated in CI)
npm run lint

# Single file or test
npx vitest run src/utils/plotting/__tests__/history.spec.ts
npx vitest run -t "round-trips a multi-step history"
```

There is no watch script in `package.json`; if you want one,
`npx vitest` (no `run`) starts watch mode.

---

## Runner config

[`vite.config.ts`](../vite.config.ts) defines `test` under the
default export. The notable knobs:

- `environment: 'happy-dom'`. Lighter than jsdom and sufficient for
  this library — there's no Vue / Vuetify here. The `Window` object
  is mostly used as `self` for `*.worker.ts` modules during
  in-process loading (see [worker tests](#worker-tests)).
- `include: ['src/**/__tests__/*.spec.ts']`. No other glob; only
  things under `__tests__/` directories count as specs.
- No `test.exclude` list. Every spec under `__tests__/` runs in CI;
  if a spec is broken, fix it rather than excluding it.

Coverage is gated at **80% all four metrics** (lines, statements,
functions, branches). The exclusion list intentionally drops:

- `dist/**`, `node_modules/**`, `**/*.d.ts` — generated / declared,
  not executable.
- `src/index.ts` — barrel re-export; nothing to cover.
- `src/types/**` — type definitions, no runtime code.
- `**/__tests__/**` — the test files themselves.
- `**/*.worker.ts` — workers are tested via `workers.spec.ts`
  but Vitest's coverage attribution doesn't see the import (the
  spec dynamically loads each worker module via `import('…')`
  inside a helper, so v8 can't link the executed lines back to
  the source file). Workers are covered behaviorally; the
  coverage-report exclusion just prevents a false-negative drop.

---

## Worker tests

The library's single biggest test-infra concern. Two distinct
mechanisms are used depending on what the spec is actually testing.

### 1. Real workers via `@vitest/web-worker`

Used in `workers.spec.ts` to verify the worker shells are wired
correctly — `self.onmessage` is set, the handler forwards to its
core, and the response shape is right.

```ts
async function loadWorker(importFn: () => Promise<unknown>) {
  ;(self as any).onmessage = null
  ;(self as any).postMessage = () => {}
  await importFn()
  const handler = (self as any).onmessage as Handler
  if (!handler) throw new Error('Worker module did not set self.onmessage')
  return (data: any): any[] => {
    const posted: any[] = []
    ;(self as any).postMessage = (msg: any) => posted.push(msg)
    handler({ data })
    return posted
  }
}

const invokeDelete = await loadWorker(() => import('../delete-data.worker'))
```

Each worker file sets `self.onmessage` at module-evaluation time,
so we import the module, grab the handler off `self`, and invoke
it synchronously. This is enough to confirm the wiring without
spawning real OS threads.

### 2. In-process worker mocks via `vi.mock(...?worker&inline)`

Used in `observation-record.spec.ts`, `observation-record-paths.spec.ts`,
and `history.spec.ts` — every spec that exercises `ObservationRecord`
end-to-end. Real workers run async (via `postMessage` round-trip);
mocking them with synchronous shims lets the spec `await
record.dispatch(...)` and read state immediately.

```ts
// Worker mocks must be registered before observation-record imports.
vi.mock('../delete-data.worker?worker&inline',
  () => import('./workerMocks').then(m => ({ default: m.MockDeleteDataWorker })))
// … one per worker
```

`workerMocks.ts` ships **mirror implementations** of every worker
kernel. They use `queueMicrotask` to dispatch results so the caller
has time to assign `onmessage` (matching the real Worker API
contract), but the work itself runs in-process.

The Vite query `?worker&inline` is what the production build uses
to inline workers as Blob URLs. Vitest doesn't resolve it natively,
so the mock takes over.

**Rule of thumb:** if your spec tests `ObservationRecord`'s
dispatch surface end-to-end, register the worker mocks. If your
spec tests just the worker handler itself, use the
`@vitest/web-worker` loader. The two approaches don't overlap.

### Keeping `workerMocks.ts` in sync

`workerMocks.ts` is a parallel implementation of every worker
kernel. When you change a worker — new arg, different result shape,
new code path — the mock has to follow. The mocks are not
generated; they're hand-written.

The safest workflow:

1. Make the change in `*.worker.ts` (and `operation-cores.ts` if
   the inline core changed too).
2. Update `workerMocks.ts` with the same change. Match the
   variable names from the worker payload (`bufferX`, `start`,
   `deleteSegment`, etc.) so the mock contract is obviously
   parallel.
3. Run `observation-record.spec.ts` — if the mocks drifted, the
   end-to-end tests will surface incorrect results. The wiring
   spec (`workers.spec.ts`) tests the real worker code so it
   alone won't catch a drifted mock; the integration specs will.

### Why workers aren't run "for real" in integration tests

`@vitest/web-worker` runs workers on the main thread synchronously
behind a `Worker`-shaped facade. It's fine for individual handler
tests (where there's no concurrent mutation) but it does NOT model
the async message queue that `ObservationRecord` relies on for
correct ordering. Using real workers in `observation-record.spec.ts`
would hang on `await`s that never resolve because the spec's
microtask loop is the same loop the worker is waiting in.

The two-tier split (real workers for wiring, in-process mocks for
integration) is the only shape that keeps both true behavior and
test ergonomics.

---

## SharedArrayBuffer caveats

`ObservationRecord` uses `SharedArrayBuffer` in browsers that
support it (gated by `crossOriginIsolated`). Happy-dom doesn't
implement SAB resize semantics (`SharedArrayBuffer.prototype.grow`),
so worker mocks operate on plain `ArrayBuffer` instances. Tests
that exercise the SAB-resize path validate "shape correct" — the
resulting `dataX` / `dataY` arrays have the right length and
content — but they don't catch SAB-specific behavior. Real-browser
SAB regressions surface in the consumer's E2E or via manual
testing.

If you're adding a code path that depends on SAB-specific semantics
(detached buffers, growth notifications, atomic ops), write a
narrowly-scoped consumer-side test in `hydroserver-qc-app` rather
than trying to model it in the qc-utils suite.

---

## Conventions

These patterns recur across the spec files. New specs should
follow them.

1. **Mock worker imports at the top.** Any spec that touches
   `ObservationRecord` must register the worker mocks **before**
   importing `observation-record`. Hoisting is automatic with
   `vi.mock(...)` (Vitest hoists `vi.mock` calls above imports),
   but readability is better when the calls live at the top of
   the file.

2. **Use `makeRecord(size)` helpers for fixtures.** The integration
   specs build deterministic uniform-grid datasets at the top of
   each spec:
   ```ts
   function makeRecord(size = 50): ObservationRecord {
     const startMs = Date.UTC(2024, 0, 1)
     const spacingMs = 15 * 60 * 1000
     const datetimes = Array.from({ length: size }, (_, i) => startMs + i * spacingMs)
     const dataValues = Array.from({ length: size }, (_, i) => i)
     return new ObservationRecord({ datetimes, dataValues })
   }
   ```
   Predictable spacing + monotonic Y means assertions can be on
   exact values, not approximate ranges.

3. **`await rec.reload()` before exercising.** `ObservationRecord`
   constructs synchronously but loads data lazily; `await reload()`
   ensures `dataX` / `dataY` are populated before the first
   dispatch. The integration specs call it in every
   `beforeEach`.

4. **Round-trip tests verify state, not just shape.** When testing
   `applyHistory`, compare full arrays:
   ```ts
   expect(Array.from(fresh.dataY)).toEqual(Array.from(rec.dataY))
   ```
   Length checks pass too easily — a misplaced index would
   produce the right length and wrong values.

5. **History assertions match by method enum.** Don't rely on
   string equality across enum changes; import the enum and
   compare values directly.

---

## Coverage thresholds

Configured in [`vite.config.ts:62-66`](../vite.config.ts). The gate
is **80% all four metrics** — no special-casing.

When coverage fails:

1. The CI report names every uncovered line.
2. For pure kernels in `operation-cores.ts`, add a targeted test
   to `operation-cores.spec.ts` — these specs are minimal and
   easy to extend.
3. For dispatch-path branches in `observation-record.ts`, the
   right home is usually `observation-record-paths.spec.ts`
   (which is structured around routing decisions) rather than
   `observation-record.spec.ts` (which is structured around the
   public surface).
4. For new public methods, the surface spec
   (`observation-record.spec.ts`) is the canonical home.

**Do not** add new entries to `coverage.exclude` to make the gate
pass; the existing entries each have a written reason and lowering
the bar by adding to the list is policy drift. If a file genuinely
should not be tested, justify it in the inline comment.

---

## CI

`.github/workflows/ci.yml` runs on every push and PR to `main`. The
job:

1. `npx tsc --noEmit` — type-check.
2. `npm run coverage` — Vitest with the 80% gate.
3. `npm run lint` — ESLint flat config (`eslint.config.js`).
4. `npm run build` — `vite build --mode prod` + `vue-tsc
   --declaration --emitDeclarationOnly` for the dist + types.

There is no separate test job. Coverage failure, lint failure, or
build failure all gate the same job.

---

## Adding new tests

### A new kernel

1. Add the pure function to `src/utils/plotting/operation-cores.ts`.
2. Add a kernel spec to
   `src/utils/plotting/__tests__/operation-cores.spec.ts` — at
   minimum, empty input, single point, typical input, and any
   edge case the kernel cares about (NaN, zero spans, overflow).
3. If the kernel has a worker wrapper, add the worker file
   (`<name>.worker.ts`) and either:
   - Update `workerMocks.ts` with a parallel mock (this is
     mandatory if `observation-record` will use the worker), OR
   - Cover the worker only via `workers.spec.ts` (only valid if
     no integration spec exercises it).
4. Add a wiring case to `workers.spec.ts` so the worker handler
   itself is covered.

### A new dispatch operation

1. Add the enum value to `EnumEditOperations` or
   `EnumFilterOperations` in `src/types/index.ts`.
2. Implement the handler in `observation-record.ts`; wire it
   into the `actions` (edit) or `filters` (filter) map.
3. Add round-trip tests to `observation-record.spec.ts`:
   - Dispatch the op and assert the resulting `history` entry
     has the right method, args, status, **and timestamp**
     (a finite epoch-ms number).
   - Test undo + redo round-trips correctly.
4. Add a history round-trip test to `history.spec.ts`:
   `serializeHistory` → `parseHistory` → `applyHistory` on a fresh
   record, then assert `dataX` / `dataY` match the original.
5. Add a route to the QC history docs
   ([QC_HISTORY.md](./QC_HISTORY.md)) under "Per-method
   serialization rules" — the args row for the new op.

### A new failure-path test

`observation-record-paths.spec.ts` is the canonical home for
routing tests:

- Worker spawn fails → fallback to inline?
- Inline core throws → `HistoryItem.execution.status === 'failed'`,
  history entry survives, redo stack preserved?
- Replay during `undo()` doesn't clobber the redo stack?

Mirror the existing pattern: induce the failure (mock a worker to
throw, pass invalid args), then assert the observable state.

---

## Maintenance checklist

When a worker handler changes:
- Update the matching `Mock*Worker` in `workerMocks.ts` to keep
  the in-process mock in sync.
- Run `observation-record.spec.ts` — drift surfaces here, not in
  `workers.spec.ts`.

When `HistoryItem` or `HistoryExecution` grows a field:
- Decide whether the field is a per-dispatch *audit* fact (mode,
  duration, dataset size) — those go on `HistoryExecution`. UI
  state that doesn't describe the dispatch itself (e.g. a
  user-set pin) belongs on `HistoryItem`.
- Decide whether it should survive `serializeHistory`. If yes
  (like `mode` or `datasetSize`), extend `projectExecution` /
  `parseExecution` in `history.ts` and add a round-trip test. If
  no (like `inFlight`, which is meaningless for a serialized op),
  document the elision in `history.ts`.
- Update the type listings in
  [API_REFERENCE.md](./API_REFERENCE.md) (`interface HistoryItem`
  and `interface HistoryExecution`) and the same blocks in
  [ARCHITECTURE.md](./ARCHITECTURE.md).

When `QcHistoryOperation` or `QcHistoryExecution` grows a field:
- Update `projectExecution` to populate it on serialize and
  `parseExecution` to validate it on load (reject malformed
  shapes — `assertFiniteNumber` and the enum guards are the
  templates).
- Update [QC_HISTORY.md](./QC_HISTORY.md): JSON example,
  per-operation entry table, the `execution` sub-fields table,
  and the per-method-serialization-rules paragraph.
- Add round-trip tests to `history.spec.ts`.

When a new Vitest major version lands:
- Re-pin `@vitest/coverage-v8` and `@vitest/web-worker` to the
  same major. The three packages must stay aligned or worker
  loading silently breaks.
- Run the suite locally; report formatters and reporter flags
  occasionally change shape.

When `vite` upgrades:
- `?worker&inline` query semantics are stable across recent major
  versions but worth re-verifying. A quick `npm test` run after
  the upgrade is sufficient.

When `happy-dom` upgrades:
- The `self.onmessage` worker-loading pattern in `workers.spec.ts`
  depends on `self` resolving to the global `Window` — verify with
  a single-spec smoke run.

When you see the SAB-resize test "passing" but real-browser
behavior diverges:
- That's the documented gap. The fix is to add a consumer-side
  E2E in `hydroserver-qc-app` exercising the path, not to
  retrofit happy-dom.

---

## Known issues

- A small handful of branches are uncovered by design:
  - `calibration.ts:279` — the `mode === 'always-worker'` return.
    Nothing in `OPERATIONS` uses this mode today; the branch is
    a documented escape hatch ("none in the current catalog").
  - `observation-record.ts` test-mode skips
    (`if (import.meta.env.MODE !== "test") await Promise.all(...)`).
    The condition is intentionally false in every test run because
    mocked workers respond via `queueMicrotask` and a real
    `Promise.all` against them would deadlock against the
    microtask scheduler.
  - `ellapsed-time.ts:12` — the dev-only `console.info` of the
    measured duration. `import.meta.env.MODE` is `"test"` in
    Vitest, never `"development"`, so the line is unreachable
    from inside the test suite.
  The TESTING.md "Adding new tests" recipes and CI gate (80% all
  metrics) are the contract; the uncovered lines above are the
  exceptions, not the rule. **Do not** widen the rule by adding
  more "dead in tests" guards without a similarly explicit
  rationale in the source.

---

## See also

- [QUALITY.md](./QUALITY.md) — what is covered, what isn't, and why
- [API_REFERENCE.md](./API_REFERENCE.md) — the public surface
- [ARCHITECTURE.md](./ARCHITECTURE.md) — kernel / worker / dispatch layering
- [QC_HISTORY.md](./QC_HISTORY.md) — the save/load format that
  the round-trip tests exercise
- [CALIBRATION.md](./CALIBRATION.md) — what `calibration.spec.ts` is testing
- [`vite.config.ts`](../vite.config.ts) — source of truth on Vitest
  config, coverage policy, and the worker-mock include rules
