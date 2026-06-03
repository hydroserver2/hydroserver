# Performance &amp; Scaling

This document answers two questions:

1. **How big a workload can the QC App handle in a single browser
   session?** (the "envelope")
2. **How does the architecture fit small-to-medium HydroServer
   deployments?** (the "fit")

It is design-review + measured-behavior, not a marketing benchmark. The
numbers are calibrated per-device by the qc-utils calibration layer, so
your envelope on a 2018 laptop is different from your envelope on a 2024
desktop — that's the whole point of the calibration mechanism.

## Where the work happens

The app is a static SPA, so "performance" almost entirely means
**in-browser computation and memory**. The HydroServer backend handles
metadata, auth, and observation transport — the QC App does not
introduce its own server-side bottleneck.

| Tier                          | Bottleneck                                                                |
|-------------------------------|---------------------------------------------------------------------------|
| Network fetch                 | HydroServer columnar pagination at 50,000 obs / page. Linear in dataset size. |
| Memory                        | `SharedArrayBuffer` holding `Float64Array` + `Float32Array` per plotted stream. |
| Filter / edit compute         | qc-utils worker pool or inline kernel, routed by per-device calibration. |
| Plot redraw                   | Plotly downsamples on zoom; sustained interactive perf is the main cost. |
| Save / load script            | JSON serialize / parse. Linear in history length, not dataset size.       |

## Memory model and limits

Each plotted stream allocates two typed arrays:

- `Float64Array` for timestamps (8 bytes / point)
- `Float32Array` for values (4 bytes / point)

So **12 bytes per observation, per plotted stream**, plus a 20k-slot
growth headroom (`INCREASE_AMOUNT` in `qc-utils`) when SAB-backed buffers
need to grow without copying.

Order-of-magnitude envelope:

| Dataset size      | Memory per stream | Notes                                                                  |
|-------------------|-------------------|------------------------------------------------------------------------|
| 50k obs           | ~0.6 MB           | Instant on any device. Inline kernels.                                 |
| 500k obs          | ~6 MB             | Comfortable. Worker layer engages on big edits.                        |
| 5 million obs     | ~60 MB            | Still feasible on a modern desktop. Initial fetch is the long pole.    |
| 50 million obs    | ~600 MB           | Browser tab approaching its memory budget. Avoid plotting more than 1 stream. Performance becomes dominated by Plotly redraw, not qc-utils. |

The architecture caps the plot at **5 concurrent streams** in the UI to
keep the multi-axis chart readable and the memory envelope predictable.

## Worker pool and calibration

Every long-running kernel ships in two flavors: an inline core
(`changeValuesCore`, `fillGapsCore`, …) and a `?worker&inline` Vite
worker variant scanning shared typed-array views in parallel.
`shouldUseWorker(...)` decides per-call:

```ts
import { ensureCalibration, shouldUseWorker, EnumEditOperations } from '@uwrl/qc-utils'
await ensureCalibration()
shouldUseWorker(EnumEditOperations.FILL_GAPS, {
  datasetSize: record.dataX.length,
  selectionSize: 0,
})
// → { useWorker: false, predictedInlineMs: 12.4, predictedWorkerMs: 53.0, ... }
```

Spawn overhead varies hugely across devices — Windows Chrome can take
~100 ms, macOS ~10 ms — so static thresholds baked into the library are
wrong for most users. The calibration layer measures three primitives
once per device (cached in `localStorage` for 30 days):

- Worker spawn roundtrip
- Inline scan throughput
- Worker scan throughput

It combines those with universal per-op complexity weights to predict
the crossover dataset size for each operation. The
`PerformanceCalibration` widget in the nav rail surfaces the cached
profile and lets users re-benchmark on demand.

The first time the app loads, `ensureCalibration()` is fired on idle, so
the first real edit already has a decision.

## SharedArrayBuffer requirement

The worker fast-path needs `SharedArrayBuffer`, which needs the page to
serve `Cross-Origin-Opener-Policy: same-origin` +
`Cross-Origin-Embedder-Policy: require-corp`. The Vite dev server and
the demo deployment both set those headers; if your CDN doesn't, the
worker layer falls back transparently to inline kernels.

The fallback is correct but slower on large edits — expect a 2-5×
slowdown on multi-hundred-thousand-point operations, and a noticeable
UI freeze on operations that take >300 ms inline.

## Network performance

Observation fetches use HydroServer's columnar format (`format=column`)
because the row format times out on ~35k-point ranges (see comments in
`src/utils/observations.ts:24`). The QC App paginates client-side at
50,000 obs / page and merges into the cache.

Key fetch optimizations already in place:

- **Cache-aware ranging.** `useObservationStore.fetchObservationsInRange`
  only requests segments outside the existing cached window (strict
  `<` / `>` comparison, see comments around `observations.ts:62`). The full
  fetched history stays in `observationsRaw`; the `ObservationRecord` keeps it
  in `rawData` and slices it to the selected `[begin, end]` range via
  `applyWindow`, so the plot, table and counts only ever touch the current
  window.
- **Loading state per datastream.** The UI shows a per-stream spinner so
  one slow fetch doesn't block the others.

Things the app does NOT do today:

- Streaming responses or WebSocket push for live updates. The QC app is
  a "snapshot QC" tool; the user reloads the window when they want
  fresher data.
- HTTP/2 prioritization or speculative prefetching.

## Plot performance

Plotly handles downsampling internally on zoom, but multi-axis
synchronized plotting at high point density is the dominant interactive
cost. Practical guidance:

- **One QC target + one or two context streams** is the sweet spot.
  Five plotted streams is the hard cap; in practice three is comfortable
  at multi-hundred-thousand points.
- **Tick alignment and viewport recompute are debounced.** See
  `src/utils/plotting/relayout.ts`.
- **Programmatic restyle is selection-only.** Full redraws push new x/y
  arrays only when the underlying data changes.

## Architectural fit for small-to-medium deployments

The QC App is well-shaped for the small-to-medium HydroServer
deployment because:

- **Zero app-side infrastructure to operate.** Static hosting + a CDN +
  a HydroServer instance. No databases, queues, or background workers
  to monitor at the app tier.
- **Independent of operator count.** Every user runs their own copy in
  the browser; there is no shared session pool to size. Adding users
  costs only bandwidth on the static bundle.
- **Cheap to redeploy.** A 30-60 s CloudFront invalidation is the
  entire promotion. Rollbacks are "redeploy the previous tag."
- **Trivial CDN edge requirements.** Two headers (`COOP` + `COEP`),
  SPA fallback, content-hashed asset caching. No origin shielding
  required, no custom Lambda@Edge.

It is **less well-shaped** when:

- **You need centrally orchestrated QC** — automated runs on a schedule,
  a queue of datastreams to process. The app is a single-operator GUI;
  for batch QC, drive `@uwrl/qc-utils` directly from a Node or Python
  (Pyodide) process and bypass the app.
- **You're QC'ing >50 million-point datastreams in one go.** Re-window
  to a smaller range; the app caps practical throughput at the browser
  memory budget, not at qc-utils kernel speed.

## What to measure

If you're operating a deployment and want to know whether it's hitting
its envelope, the things to watch:

1. **CDN 4xx / 5xx rate.** Should be ~0 outside backend incidents.
2. **HydroServer backend `/observations` p95 latency.** This is the
   dominant interactive cost on large fetches.
3. **In-browser console for `dispatch` failures.** Failed worker spawns
   surface here; they indicate either a SAB-disabled origin or a corrupt
   bundle.
4. **The calibration widget** on representative user devices. If
   `predictedInlineMs` is much higher than reality, the calibration is
   stale — re-benchmark.

Today there is no automated reporter that aggregates these numbers off
the user's machine (see [DEPLOYMENT.md "Operational observability"](./DEPLOYMENT.md#operational-observability));
collection is manual until you wire in a RUM service.

## Community evidence

The QC App is operated today by the HydroServer / CIROH community at
small-to-medium scale (hundreds of datastreams per workspace, observation
windows in the hundreds-of-thousands range). The
`playground.hydroserver.org` deployment is the public reference.

There is no published large-scale benchmark suite. If you're evaluating
the app for a >1M-operator-monthly workload, treat that as an open
question — the architecture has nothing structurally preventing it
(every user has their own browser), but bandwidth and HydroServer
backend capacity are the constraints, not the QC App itself.

## See also

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [DEPLOYMENT.md](./DEPLOYMENT.md)
- [QUALITY.md](./QUALITY.md)
