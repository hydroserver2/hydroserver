# Developer Onboarding

Goal of this doc: get a new contributor from "fresh checkout" to "I can
make a change and verify it" in under an hour, and tell them honestly
where the documentation gaps are so they don't waste a day finding out.

## Prerequisites

| Tool      | Version                                   | Notes                                                        |
| --------- | ----------------------------------------- | ------------------------------------------------------------ |
| Node.js   | 20 LTS or 23.x                            | CI runs 20. Either works.                                   |
| npm       | 10+                                       | Ships with Node.                                             |
| Git       | any recent                                |                                                              |
| A browser | Chrome 111+ / Firefox 119+ / Safari 16.4+ | Required for `SharedArrayBuffer` and typed-array `resize()`. |

You do **not** need Docker. For frontend-only work you can run the Data
Management app and QC app against a deployed HydroServer
(`playground.hydroserver.org` by default).

## First-day setup

```bash
git clone https://github.com/hydroserver2/hydroserver.git
cd hydroserver
npm install
```

```bash
cd apps/qc-app
npm run dev          # internal QC dev server at http://127.0.0.1:5173
```

For the full app flow, start both frontends and open QC through Data
Management at `http://127.0.0.1:1203/qc/`. The shared VS Code task
`Start Frontends Against Playground` starts both apps pointed at
`https://playground.hydroserver.org`.

**Use `http://127.0.0.1:1203`, not `http://localhost:1203`, for the Data
Management entrypoint.** The playground backend's CORS allowlist pins the
IP literal.

If you hit a blank page with `Failed to fetch app settings` in the
console, it's almost always one of:

1. Hitting `localhost:` instead of `127.0.0.1:`.
2. The backend doesn't serve `Cross-Origin-Resource-Policy` and COOP/COEP
   is on — try `VITE_APP_DISABLE_COOP=1`.

## Project tour, in reading order

Read these files in order:

1. `README.md` — what the app does + config.
2. `docs/ARCHITECTURE.md` — stack, source layout, data flow.
3. `src/App.vue` and `src/main.ts` — entry point, plugin wiring.
4. `src/pages/Home.vue` and `src/components/VisualizeData.vue` — the
   landing experience.
5. `src/store/dataVisualization.ts` and `src/store/plotly.ts` — the two
   stores that hold "what the user sees on the plot."
6. `src/composables/useFilterDispatch.ts` and `useQcSubmission.ts` —
   the two end-to-end flows worth tracing.
7. `packages/qc-utils/src/utils/plotting/observation-record.ts` — the QC engine's
   dispatch surface. You don't need to read the kernels; the dispatcher
   is the contract.

## Day-to-day workflow

From `apps/qc-app`:

```bash
npm run dev          # QC vite dev server, http://127.0.0.1:5173
npm test                  # vitest, watch mode
npm run coverage          # vitest one-shot + v8 coverage (80% threshold)
npm run e2e               # playwright, headless (CI mode); add -- --ui or -- --headed
```

For a production-style QC app build, build `qc-utils` first:

```bash
cd packages/qc-utils
npm run build

cd ../../apps/qc-app
npm run build
```

Run `npm run coverage` before you push — that's what CI gates on.

### Working with qc-utils changes

The QC app dev server aliases `@uwrl/qc-utils` directly to
`packages/qc-utils/src`, so you do not need to build `qc-utils` while
developing locally:

```bash
npm run dev
```

Edits under `packages/qc-utils/src` are served from source in dev mode.
Build `qc-utils` only before running the QC app production build or when
you need to verify the published package artifacts.

## Coding conventions

- TypeScript strict mode. No `any` without a comment explaining why.
- Vue 3 Composition API with `<script setup>`. Options API is not used.
- Pinia stores for cross-component state; component-local state stays in
  `ref` / `reactive` inside the component.
- Comments only for the non-obvious _why_. Don't restate the code.
- Commit format: `{type}({scope}): {description}` — `feat`, `fix`,
  `test`, `refactor`, `perf`, `docs`, `style`, `chore`.

## Documentation gaps

1. **Result qualifiers are partial.** The `QualifyingComments` op panel
   exists and writes to the in-memory history, but the submit path
   (`useQcSubmission.ts`) currently serializes only `phenomenonTime` and
   `result` — qualifier codes are deferred pending the HydroServer API
   adding a workable columnar response. There's a TODO in
   `useQcSubmission.ts:42` that points at this.
2. **No load-testing artifacts.** "How big a datastream can you QC in
   one session?" is answered empirically per browser via the calibration
   pass, but there is no published "this is the supported envelope"
   document. See [PERFORMANCE.md](./PERFORMANCE.md) for the design
   characteristics, but expect to measure your own workloads.

## Where to ask for help

- [Issue tracker](https://github.com/hydroserver2/hydroserver/issues) —
  bugs and feature requests for the HydroServer project as a whole.
- The qc-utils repo's issues for QC engine bugs.
- The HydroServer documentation site at
  <https://hydroserver2.github.io/hydroserver/> — the operator-facing
  HydroServer docs cover the backend the app talks to.

## See also

- [README](../README.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [DEPLOYMENT.md](./DEPLOYMENT.md)
- [API_REFERENCE.md](./API_REFERENCE.md)
- [QUALITY.md](./QUALITY.md)
- [PERFORMANCE.md](./PERFORMANCE.md)
- [USER_GUIDE.md](./USER_GUIDE.md)
