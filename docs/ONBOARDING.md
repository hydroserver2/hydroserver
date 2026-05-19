# Developer Onboarding — `@uwrl/qc-utils`

Goal: get you from "fresh clone" to "I changed a kernel, the consumer
app sees the change, and CI is green" in under an hour. Plus an honest
list of the documentation gaps so you don't waste a day finding out.

## Prerequisites

| Tool       | Version          | Notes                                                     |
|------------|------------------|-----------------------------------------------------------|
| Node.js    | 20 LTS           | CI runs Node 20. Newer is fine for dev.                   |
| npm        | 10+              | Ships with Node.                                          |
| Git        | any recent       |                                                           |
| A browser  | Chrome 111+ / Firefox 119+ / Safari 16.4+ | Required for `SharedArrayBuffer`, typed-array `resize()`, and `SAB.grow()`. |

You do **not** need Docker, Python, or any backend infrastructure.

## First-day setup

```bash
git clone https://github.com/hydroserver2/qc-utils.git
cd qc-utils
npm install
npm test                # vitest, full suite
npm run coverage        # vitest + v8 coverage, 80% threshold
npm run lint            # eslint
npm run build           # vite build + .d.ts emit → dist/
```

That's the entire flow. If CI gates pass locally, your branch will
pass in CI.

## Linked-dev with hydroserver-qc-app

The typical workflow when you're tweaking a kernel and want to verify
end-to-end behavior in the consumer app:

```bash
# Terminal 1 — qc-utils
cd qc-utils
npm link                # registers @uwrl/qc-utils in the local npm registry
npm run dev             # vite build --watch — rebuilds dist/ in ~1s

# Terminal 2 — qc-app
cd ../hydroserver-qc-app
npm run link-qc-utils   # npm link @uwrl/qc-utils
npm run dev             # http://127.0.0.1:1203
```

Refresh the browser to pick up `qc-utils` changes — HMR doesn't propagate
through linked packages. If type errors look stale after editing
`src/types/index.ts` or other declarations, run `npm run build` once in
qc-utils to refresh `.d.ts`.

To unlink: `cd hydroserver-qc-app && npm unlink @uwrl/qc-utils && npm install`.

## Project tour, in reading order

Read in this order:

1. `README.md` — quick-start + concepts.
2. `docs/ARCHITECTURE.md` — stack and structure.
3. `src/types/index.ts` — the enums + types that drive everything.
4. `src/utils/plotting/observation-record.ts` — the dispatch surface.
   You don't need to read every kernel; the dispatcher *is* the contract.
5. `src/utils/plotting/operation-cores.ts` — the inline kernels. Each
   is a pure function over typed arrays; reading one is enough to
   understand the pattern.
6. `src/utils/plotting/calibration.ts` and `docs/CALIBRATION.md` — how
   per-call worker / inline routing works.
7. `src/utils/plotting/script.ts` and `docs/HISTORY_SCRIPT.md` — the
   save / load format.

## Day-to-day workflow

| Script              | Purpose                                                |
|---------------------|--------------------------------------------------------|
| `npm run dev`       | Watch-mode bundler. Rebuilds `dist/` on every save.    |
| `npm run build`     | Production build + `.d.ts` emit. Writes `stats.html`.  |
| `npm test`          | Vitest, full suite (no watch).                         |
| `npm run coverage`  | Vitest + v8 coverage, 80% threshold.                   |
| `npm run lint`      | ESLint.                                                |
| `npm run lint:fix`  | ESLint with auto-fix.                                  |
| `npm run pub`       | `npm publish --access public` — release to npm.        |
| `npm run up`        | `taze major -I` — major-bump audit.                    |

CI runs `tsc --noEmit → coverage → lint → build` on every push and PR
to main. Match that locally before pushing.

## Adding a new operation

The pattern, learned by reading existing ops:

1. Add the enum entry in `src/types/index.ts` (either
   `EnumEditOperations` or `EnumFilterOperations`).
2. Implement the **inline core** in `src/utils/plotting/operation-cores.ts`
   as a pure function over typed arrays.
3. Implement the **worker variant** as `src/utils/plotting/<op>.worker.ts`.
   Copy the structure of an existing worker (e.g.
   `value-threshold.worker.ts`).
4. Wire it into `observation-record.ts`:
   - Import the worker via `?worker&inline`.
   - Add a handler in `dispatchAction` / `dispatchFilter` that calls
     `shouldUseWorker(...)` and routes accordingly.
5. Add a complexity weight in `calibration.ts` (the per-op constant).
   This is universal — measure once on a representative dataset and
   bake it in.
6. Write tests:
   - Unit test the core in `__tests__/operation-cores.spec.ts`.
   - Worker integration test in `__tests__/workers.spec.ts`.
   - Dispatch + history test in `__tests__/observation-record.spec.ts`.
   - Calibration prediction test in `__tests__/calibration.spec.ts`.
7. If the op should be saveable, make sure `serializeHistory` and
   `applyScript` round-trip it. Both already handle every enum, but
   verify with a test in `__tests__/script.spec.ts`.
8. Update the consumer (qc-app) to expose a panel for the new op.

## LSP-first navigation

Use:

- `goToDefinition` / `goToImplementation` to jump.
- `findReferences` before renaming an exported symbol — there are
  consumers outside this repo.
- `workspaceSymbol` to find where something is defined.

## Coding conventions

- **TypeScript strict mode.** No `any` without a comment.
- **Pure functions for kernels.** Each inline core in
  `operation-cores.ts` takes typed-array views in, mutates / produces
  typed-array views out. No global state.
- **Workers are inlined (`?worker&inline`).** This is intentional — each
  worker bundle becomes a Blob URL at build time so consumers don't have
  to configure their own worker host.
- **Comments only when they explain the non-obvious *why*.** The
  invariants worth flagging (SAB availability gate in `makeBuffer`,
  always-inline short-circuits, the 30-day calibration TTL) are already
  commented.
- **No band-aid solutions.** Root-cause, not workaround.

## Where the documentation is solid

- `README.md` is the primary entry point — exhaustive on install, quick-
  start, concepts, and the public API surface.
- [HISTORY_SCRIPT.md](./HISTORY_SCRIPT.md) and
  [CALIBRATION.md](./CALIBRATION.md) are the two design docs you actually
  reach for. They are long, current, and accurate.
- Inline comments are heaviest in `calibration.ts` and
  `observation-record.ts` — the two files where the *why* matters most.

## Documentation gaps a new team will hit

- **The per-worker bundle structure** is not narrated end-to-end. Each
  worker file is short, but the way Vite inlines them into the published
  bundle is implicit. `stats.html` (emitted on build) is the only
  authoritative view.
- **No published per-op cost table.** [CALIBRATION.md](./CALIBRATION.md)
  documents the methodology and shows representative numbers, but the
  actual current complexity weights live as constants in
  `calibration.ts`. If they drift, no doc captures the change.
- **The `Snackbar` notification helper** is exported but is really a
  consumer convenience for the qc-app. A library consumer doesn't need
  it; the export is preserved for compatibility.

## Where to ask for help

- [Issue tracker](https://github.com/hydroserver2/qc-utils/issues).
- HydroServer organization on GitHub: <https://github.com/hydroserver2>.

## See also

- [README](../README.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [API_REFERENCE.md](./API_REFERENCE.md)
- [DEPLOYMENT.md](./DEPLOYMENT.md)
- [PERFORMANCE.md](./PERFORMANCE.md)
- [QUALITY.md](./QUALITY.md)
- [HISTORY_SCRIPT.md](./HISTORY_SCRIPT.md)
- [CALIBRATION.md](./CALIBRATION.md)
