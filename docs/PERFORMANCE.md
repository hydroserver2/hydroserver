# Performance &amp; Scaling

`@uwrl/qc-utils` is the part of the QC pipeline that does the actual
work. This document covers how it performs and where its scaling
limits actually are. For the consumer-app perspective, see
[hydroserver-qc-app PERFORMANCE.md](../../hydroserver-qc-app/docs/PERFORMANCE.md).

## What "fast" means here

The library has two operating regimes:

1. **Inline mode** — pure typed-array scans on the main thread. Sub-
   millisecond for small ops, single-digit milliseconds for ops on
   ~10⁵ points, predictable, no spawn overhead.
2. **Worker mode** — same kernel, run across `navigator.hardwareConcurrency`
   workers reading SAB-backed views. Speedup is roughly linear in the
   number of workers minus the spawn cost.

The choice is made per call by `shouldUseWorker(...)`, which reads
device-calibrated primitives plus per-op complexity weights. The full
methodology is in [CALIBRATION.md](./CALIBRATION.md).

## Memory model

A single `ObservationRecord` allocates two typed arrays:

- `Float64Array` for timestamps — 8 bytes / point
- `Float32Array` for values — 4 bytes / point

So **12 bytes per observation**, plus a 20,000-slot growth headroom
(`INCREASE_AMOUNT`) reserved on initial allocation when the buffer
exposes `maxByteLength`. The grow strategy uses
`SharedArrayBuffer.grow()` + typed-array `resize()` to avoid copies on
each insertion batch.

When `SharedArrayBuffer` is unavailable, the buffer is a plain
`ArrayBuffer`. Same shape, same cost, but workers cannot share it —
the dispatcher routes everything inline.

## Operation cost (orders of magnitude)

These are the right ballpark on a modern desktop browser. Treat them as
"shape of the curve," not benchmark commitments — the calibration layer
measures real numbers per device.

| Op                          | Inline at 10⁴ pts | Inline at 10⁵ pts | Worker at 10⁶ pts | Notes                                                                 |
|-----------------------------|-------------------|--------------------|--------------------|-----------------------------------------------------------------------|
| `VALUE_THRESHOLD`           | <1 ms             | ~3 ms              | ~15 ms             | O(n) scan. The calibration reference kernel.                          |
| `CHANGE`, `RATE_OF_CHANGE`  | <1 ms             | ~3 ms              | ~15 ms             | O(n) scan over adjacent pairs.                                        |
| `FIND_GAPS`                 | <1 ms             | ~2 ms              | ~10 ms             | O(n) but cheaper per element.                                         |
| `PERSISTENCE`               | <1 ms             | ~4 ms              | ~20 ms             | O(n) with run-length book-keeping.                                    |
| `DATETIME_RANGE`            | <1 ms             | <1 ms              | <1 ms              | Always inline — two binary searches.                                  |
| `SELECTION`                 | <1 ms             | <1 ms              | <1 ms              | Always inline — just stores indices.                                  |
| `CHANGE_VALUES`             | <1 ms             | ~2 ms              | ~10 ms             | O(\|selection\|) scatter writes.                                      |
| `INTERPOLATE`               | <1 ms             | ~3 ms              | ~15 ms             | O(\|selection\|) over grouped runs.                                   |
| `DRIFT_CORRECTION`          | <1 ms             | ~3 ms              | ~15 ms             | O(\|selection\|) over grouped runs.                                   |
| `DELETE_POINTS`             | ~1 ms             | ~5 ms              | ~25 ms             | Single skip-on-delete pass over all points.                           |
| `ADD_POINTS`                | ~1 ms             | ~6 ms              | ~30 ms             | Sort-merge into existing dataset.                                     |
| `SHIFT_DATETIMES`           | ~1 ms             | ~6 ms              | ~30 ms             | Combined delete + add under the hood.                                 |
| `FILL_GAPS`                 | depends on gaps   | depends on gaps    | depends on gaps    | Gap detection is O(n); fill cost scales with the number of inserted points. |
| Worker spawn overhead       | —                 | —                  | ~10-100 ms one-time | Highly device-dependent. macOS ~10 ms, Windows ~100 ms.              |

Inline is always faster below the crossover; worker wins for big
datasets where the spawn cost amortizes. Calibration picks the
crossover per device.

## Scaling envelope

| Dataset size | Memory / stream | Practical experience                                                                |
|--------------|-----------------|--------------------------------------------------------------------------------------|
| 50k obs      | ~0.6 MB         | Instant. Everything inline.                                                          |
| 500k obs     | ~6 MB           | Comfortable. Workers kick in on big edits.                                           |
| 5M obs       | ~60 MB          | Feasible on a modern desktop. Network fetch dominates the wall-clock time.           |
| 50M obs      | ~600 MB         | Tab approaching its memory budget. Re-window in the consumer.                        |

The qc-app's "5 plotted streams" cap is a consumer-side decision —
qc-utils itself doesn't impose one. If you build a consumer that wants
20 records in memory, you'll hit the browser's per-tab memory ceiling
long before any kernel-side limit.

## Scaling shape

`ObservationRecord` is **a single-process, single-record** data
structure. There is no shared state across records, no cross-record
coordination, no lock contention to worry about — you can have many
`ObservationRecord` instances side-by-side with no interference. The
worker pool is per-call (workers are spawned per op when needed and
terminated), so concurrent records do not fight over a pool slot.

There is no concept of distributed compute. The library does not know
about networks. If you need to QC datasets that don't fit in one
browser tab, the right move is to split the work in the consumer and
run multiple `ObservationRecord`s, possibly across multiple tabs or
processes. Each instance is independent.

## Architectural fit for small-to-medium deployments

This is the layer that genuinely scales for hydrology workloads at the
small-to-medium tier:

- **Single-operator-on-laptop is the primary case.** Browser CPU +
  RAM is the budget; the library lives within that budget by design.
- **Worker parallelism is opportunistic.** When the host serves
  COOP/COEP, workers help; when it doesn't, inline mode is correct,
  just slower.
- **Streaming is not a goal.** The library expects you to hand it the
  full window for the current QC session in memory. Re-windowing is
  the consumer's responsibility.

It is **less well-shaped** for:

- **Cluster / distributed QC.** No shared state, no IPC, no
  serialization protocol beyond `QcHistory`. If you need that, build
  a coordinator in your own runtime that drives many
  `ObservationRecord` workers.
- **Real-time streaming QC.** The replay-based undo model is O(history
  length); on a stream that never ends, history grows unbounded.
  Acceptable for sessions of <1000 ops; not designed for batch
  pipelines that accumulate millions.
- **Datasets that don't fit in a Float32.** Values use Float32 — sensor
  readings normally do. If you have a domain with Float64 value
  precision requirements, this library is not the right fit without a
  fork.

## Community evidence

The library is operated today inside `hydroserver-qc-app` at the
small-to-medium scale (hundreds of datastreams per workspace, windows
in the 10⁵-10⁶ obs range). There is no published large-scale benchmark
because all benchmarks are device-relative — the calibration layer is
how a deployment learns its own scaling shape.

If you're evaluating for a workload outside this envelope, the
recommended first step is to run `runBenchmarks()` on a representative
device and inspect the resulting `DeviceProfile.spawnOverheadMs` /
`workerThroughput`. Those two numbers tell you whether your target
environment has a usable worker path; the rest of the envelope follows
from typed-array memory math.

## What we measure in CI

Today: nothing performance-related. CI gates on correctness, lint, and
coverage. There is no historical perf benchmark in CI today; a
calibration / kernel regression would only be caught by manual smoke
testing in the consumer. This is a known gap — see
[QUALITY.md](./QUALITY.md).

## See also

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [CALIBRATION.md](./CALIBRATION.md) — the detailed dispatch methodology
- [API_REFERENCE.md](./API_REFERENCE.md)
- [QUALITY.md](./QUALITY.md)
- [hydroserver-qc-app PERFORMANCE.md](../../hydroserver-qc-app/docs/PERFORMANCE.md)
