# Worker / Inline Calibration

This document describes how `@uwrl/qc-utils` decides, per operation
and per user, whether to run a QC operation on a web worker or inline
on the main thread — and how the decision gets tuned to each device.

If you only want to use it, jump to [**Public API**](#public-api).
If you're here to understand or tune it, read on.

---

## Why calibrate

Every operation in `ObservationRecord` has a worker variant (see
`src/utils/plotting/*.worker.ts`). Spawning a worker is not free:

| Platform        | Typical spawn cost |
| --------------- | ------------------ |
| macOS Chrome    | ~10 ms             |
| Linux Chrome    | ~20 ms             |
| Windows Chrome  | ~100 ms            |
| Budget Android  | 50–200 ms          |

For a **small** edit — say, multiplying 12 selected values by 1.05 —
that 100 ms is pure overhead. The main thread could have done the
write in microseconds. For a **large** filter — threshold-scan of a
million points — the spawn cost is a rounding error and the multi-
worker parallelism wins by 4–8×.

The crossover depends on two things:

1. **The operation.** `CHANGE_VALUES` touches one index per element.
   `DATETIME_RANGE` runs a binary search. `INTERPOLATE` multiplies
   and divides per group. Per-element cost varies ~3× across the
   catalog.
2. **The device.** Spawn cost on a Pixelbook is not spawn cost on an
   M3 MacBook. Static thresholds baked into the library would be
   wrong for most users.

The calibration feature measures (1) during development and ships
it with the library. It measures (2) at runtime on the user's
machine and caches the result in `localStorage`.

---

## The dispatch formula

`shouldUseWorker(op, signals)` answers: would inline beat worker for
this call?

```
predictedInlineMs  = weight[op] * N / inlineThroughput
predictedWorkerMs  = spawnOverheadMs
                   + weight[op] * N / (workerThroughput * parallelism)

useWorker = predictedInlineMs > predictedWorkerMs
```

Where:

- `N` = `estimateWorkUnits(op, signals)` — see [cost estimators](#cost-estimators)
- `weight[op]` — per-operation constant, see [operation table](#operation-table)
- `spawnOverheadMs`, `inlineThroughput`, `workerThroughput` —
  device primitives, see [the three measurements](#the-three-measurements)
- `parallelism` — `navigator.hardwareConcurrency`, capped sensibly

Everything is closed-form. The decision costs no measurable time at
dispatch.

---

## The three measurements

Every device gets profiled once (then cached for 30 days) to produce:

| Primitive           | Meaning                                                            | Typical values       |
| ------------------- | ------------------------------------------------------------------ | -------------------- |
| `spawnOverheadMs`   | Wall-clock ms for one roundtrip: construct worker → tiny postMessage → terminate | 10–150 ms |
| `inlineThroughput`  | Elements/ms on main thread, using `VALUE_THRESHOLD` as reference   | 20 000–200 000       |
| `workerThroughput`  | Elements/ms inside a worker, measured over a big enough buffer that spawn cost is amortized | 40 000–400 000 |

All three are computed as the median of three samples. The benchmark
uses the `VALUE_THRESHOLD` kernel because it already has both a
worker and an inline core (`valueThresholdCore`), so we can compare
the two paths directly without shipping a dedicated fixture.

If `SharedArrayBuffer` isn't available (missing COOP/COEP headers
in the embedding context), workers can't share the Y view — the
calibration short-circuits and every op runs inline.

---

## Operation table

Every op lives in one of three modes:

- **`always-inline`** — never benefits from worker. Binary searches,
  single-shot bookkeeping, small tight loops.
- **`always-worker`** — the worker path does nontrivial work (buffer
  allocation, shard merges, resizable `SharedArrayBuffer` operations)
  that hasn't been ported to an inline fallback yet. Calibration
  still plans for future promotion.
- **`calibrated`** — the dispatch site asks `shouldUseWorker()` per
  call and branches accordingly.

| Operation                 | Mode             | Weight | Primary cost driver                          | Notes                                            |
| ------------------------- | ---------------- | ------ | -------------------------------------------- | ------------------------------------------------ |
| `SELECTION`               | always-inline    | 0      | none                                         | Pure history entry                               |
| `DATETIME_RANGE`          | always-inline    | 0      | `O(log n)` binary search                     | Worker spawn dwarfs a 20-ns search               |
| `ASSIGN_VALUES_BULK`      | always-inline    | 0      | `O(k)` tight loop                            | Single-shot; already inlined                     |
| `ASSIGN_DATETIMES_BULK`   | always-inline    | 0      | composes delete + add                        | Those downstream ops handle their own dispatch   |
| `VALUE_THRESHOLD`         | calibrated       | 1.0    | `datasetSize`                                | Reference kernel — baseline weight               |
| `CHANGE`                  | calibrated       | 1.1    | `datasetSize`                                | One subtraction per step                         |
| `RATE_OF_CHANGE`          | calibrated       | 1.4    | `datasetSize`                                | Division + abs per step                          |
| `FIND_GAPS`               | calibrated       | 0.9    | `datasetSize`                                | Scan X only; usually few gaps                    |
| `PERSISTENCE`             | calibrated       | 1.3    | `datasetSize`                                | Chunk-boundary stitch adds constant factor       |
| `CHANGE_VALUES`           | calibrated       | 0.7    | `selectionSize`                              | In-place arithmetic, cache-friendly              |
| `INTERPOLATE`             | always-worker    | 1.5    | `selectionSize` + per-group anchor math      | Inline fallback pending (see TODOs below)        |
| `DRIFT_CORRECTION`        | calibrated       | 1.2    | total range extent                           | O(range total) in-place math; one pass per range |
| `SHIFT_DATETIMES`         | always-worker    | 1.1    | `selectionSize`                              | Inline fallback pending                          |
| `ADD_POINTS`              | always-worker    | 1.8    | `datasetSize + k·log(datasetSize)`           | Merges + resize; inline fallback pending         |
| `DELETE_POINTS`           | always-worker    | 1.4    | `datasetSize`                                | Segmented copy + resize; inline fallback pending |
| `FILL_GAPS`               | always-worker    | 1.3    | `datasetSize + fill count`                   | Output buffer sizing; inline fallback pending    |

### Why these modes

**Always-inline ops** don't actually benefit from workers because
they don't have a useful amount of work to distribute. `SELECTION`
writes one history record. `DATETIME_RANGE` does `O(log n)` binary
search; at `n = 10_000_000` that's 24 comparisons, faster than
constructing a `Worker` object. `ASSIGN_*_BULK` runs one tight loop
per call — no sharding shape to exploit.

**Calibrated ops** are the payoff zone. They have an inline core
(`src/utils/plotting/operation-cores.ts`) and the dispatch site
checks `shouldUseWorker()` before spawning. Examples:

- `VALUE_THRESHOLD` on 5 000 points: inline ~0.1 ms, worker ~110 ms
  on Windows. **Inline wins by 1100×.**
- `VALUE_THRESHOLD` on 5 000 000 points: inline ~100 ms, worker ~20
  ms across 8 cores. **Worker wins by 5×.**

The crossover sits roughly at `spawnOverheadMs * inlineThroughput`
elements — ~50 000 on Windows, ~500 000 on Mac — but the formula
accounts for per-op `weight` and selection size, so you don't have to
remember those numbers.

**Always-worker ops** are the TODO list. Every one of them has a
worker implementation that allocates large `SharedArrayBuffer`s,
shards inserts/deletes across workers, then either writes in place
or swaps in new buffers. Porting these to an inline fallback is
mechanical but not trivial — follow the pattern established for
`VALUE_THRESHOLD`:

1. Extract the hot loop into a pure function in `operation-cores.ts`.
2. Update the worker file to call the core.
3. In `observation-record.ts`, replace the pre-existing dispatch with
   a `shouldUseWorker()` check; on `useWorker: false`, call the core
   directly over `[0, dataX.length)` (or the appropriate range).

For ops that allocate a new buffer (`ADD_POINTS`, `DELETE_POINTS`,
`FILL_GAPS`), the inline fallback can skip the `SharedArrayBuffer`
allocation entirely and use a regular `ArrayBuffer` since nothing
else will read it.

---

## Cost estimators

`estimateWorkUnits(op, signals)` returns an integer "how much work"
to feed into the formula. It's closed-form and reads values the
dispatch site already has:

```ts
CHANGE_VALUES       → selectionSize
INTERPOLATE         → selectionSize
SHIFT_DATETIMES     → selectionSize
DRIFT_CORRECTION    → summed range extent (passed as selectionSize)
DELETE_POINTS       → selectionSize + datasetSize * 0.25
ADD_POINTS          → datasetSize + selectionSize * log2(datasetSize)
everything else     → datasetSize      (default: full-scan ops)
```

The approximations are deliberate. Getting within a factor of ~2 of
actual cost is enough to pick the right side of a 10× crossover.

---

## Public API

From `@uwrl/qc-utils`:

```ts
import {
  shouldUseWorker,           // the decision function — used internally
  ensureCalibration,         // idempotent benchmark; call at boot + on user action
  runBenchmarks,             // low-level: measure without caching/storing
  getCalibration,            // read the active DeviceProfile
  getLastBenchmarkDetail,    // raw sample arrays (for dev UI)
  getOperationTable,         // ordered op + mode + weight table
  onCalibrationChange,       // listener fired after each recalibrate
  clearCalibration,          // drop the cached profile
} from '@uwrl/qc-utils'
```

### Typical integration (from qc-app)

```ts
// Kicked off at idle time so startup latency stays flat
import { ensureCalibration } from '@uwrl/qc-utils'
requestIdleCallback(() => {
  ensureCalibration().catch((err) => console.warn('calibration failed', err))
})
```

### User-facing recalibrate button

```ts
import { ensureCalibration, getCalibration, onCalibrationChange } from '@uwrl/qc-utils'

async function onClickRecalibrate() {
  await ensureCalibration({ force: true })
  // active profile is now updated; `onCalibrationChange` fires too
}
```

### Decision surface (internal)

`shouldUseWorker(op, signals)` is called only from inside
`ObservationRecord`. App code shouldn't need it — dispatch picks
the right path automatically.

---

## Storage

The active profile is JSON-serialised to `localStorage` under

```
qc-utils:calibration:v1
```

The `v1` suffix is the schema version — bump it in `CALIBRATION_VERSION`
when the `DeviceProfile` shape changes to automatically invalidate
stale entries. Storage failures (quota, private mode) are swallowed;
the in-memory profile still drives the session, the user just needs
to recalibrate on each reload.

Stale detection re-runs the benchmark after 30 days so machines that
slow down (thermals, OS updates, background load) don't stick with
an old profile forever.

---

## Troubleshooting

**"The Recalibrate button spins forever."** Check the DevTools
console: the benchmark needs `SharedArrayBuffer`, which requires
cross-origin isolation (`Cross-Origin-Opener-Policy: same-origin`
and `Cross-Origin-Embedder-Policy: require-corp` response headers).
If SAB is unavailable the benchmark short-circuits to defaults
instantly — there's no spin to hang on.

**"Small edits still feel slow."** Confirm calibration ran:
`localStorage.getItem('qc-utils:calibration:v1')` should have a
recent `measuredAt`. If the inline path is selected (check the dev
popover) and it's still slow, the bottleneck is downstream
(plot redraw, Vue reactivity) rather than in qc-utils.

**"Calibration results look wildly different from run to run."**
Thermal throttling or heavy background load during the benchmark
window. Close demanding tabs and re-run; the 30-day staleness
trigger exists precisely so a bad measurement doesn't stick.

---

## Extending

### Promoting an `always-worker` op to `calibrated`

1. Identify the worker's hot loop. Most are ~20 lines.
2. Move the loop to `operation-cores.ts` as a pure exported function.
3. Update the worker to `import` and call the core — no behaviour
   change.
4. In `observation-record.ts`'s dispatch method for that op, add:
   ```ts
   const decision = shouldUseWorker(EnumEditOperations.FOO, {
     datasetSize: this.dataset.source.y.length,
     selectionSize: selection?.length,
   });
   if (!decision.useWorker) {
     fooCore(/* whole-range args */);
     return;
   }
   ```
5. Flip the op's `mode` in `OPERATION_TABLE` (calibration.ts) from
   `'always-worker'` to `'calibrated'`.
6. Verify the unit tests, then calibrate locally to confirm
   crossover matches expectation.

### Adjusting weights

`OPERATION_TABLE` weights are relative to the reference `VALUE_THRESHOLD`
scan. If profiling reveals a weight is off by a factor of 2+, update
the number — weights are shipped with the library because they describe
the algorithm, not the hardware.

### Adding a new signal

`DispatchSignals` is an open interface. If a future op's cost
depends on something like "number of consecutive groups" or "gap
count", add the field there and extend `estimateWorkUnits()`.
