# Codebase Quality &amp; Maintainability

What a new team would need to know about the shape of `@uwrl/qc-utils`:
readability standards, test coverage, and the technical debt worth
surfacing rather than discovering.

## Code style and readability

- **TypeScript strict mode**, type-checked in CI with `tsc --noEmit`.
- **ESLint flat config** (`eslint.config.js`) — typescript-eslint +
  prettier integration. CI gates on `npm run lint`.
- **Prettier** for formatting.
- **Pure functions for kernels.** Each inline core in
  `operation-cores.ts` takes typed-array views in, returns / mutates
  typed-array views out. No global state, no DOM, no side effects
  beyond the buffer.
- **Workers are inlined.** Every `?worker&inline` import becomes a
  Blob URL at build time so consumers don't have to configure their
  own worker loader. This is what makes the package "single-import."
- **Comments only on the non-obvious *why*.** The heaviest commenting
  is in `calibration.ts` (the design rationale would be opaque
  without it) and `observation-record.ts` (the SAB availability gate
  in `makeBuffer`, the always-inline short-circuits).

## Test coverage

CI gate is **Vitest + v8 coverage, ≥80% all four metrics**. The suite
is split:

| Test file                                       | Surface covered                                            |
|-------------------------------------------------|------------------------------------------------------------|
| `observation-record.spec.ts`                    | Public dispatch surface, undo / redo / reload, history.    |
| `observation-record-paths.spec.ts`              | Inline vs worker routing paths, both success and failure.  |
| `operation-cores.spec.ts`                       | Every inline kernel, edge cases (empty, single point, NaN).|
| `workers.spec.ts`                               | Every worker variant via `@vitest/web-worker`.             |
| `calibration.spec.ts`                           | Benchmark math, fallback profile, decision predictions.    |
| `history.spec.ts`                                | `serializeHistory` / `parseHistory` / `applyHistory` round-trip + per-op failures. |
| `format.spec.ts`, `ellapsed-time.spec.ts`, `observations.spec.ts`, `notifications.spec.ts` | Helpers.                                |

`@vitest/web-worker` runs the worker code in-process, so worker
behavior is testable without spawning real OS workers.

### What is NOT covered

- **Cross-browser behavior of `SharedArrayBuffer.grow()`** — happy-dom
  doesn't model the resize semantics. We test the JS-level call and
  fall back to a "shape correct" assertion; real-browser regressions
  surface only in the consumer's E2E or via manual testing.
- **Performance**. No perf-regression CI; the calibration layer is
  benchmarked but no historical baseline is asserted in CI.

## Areas of technical debt

### 1. No automated perf regression suite

The calibration layer measures per-device; CI does not assert a
baseline. A kernel-level regression — say, an O(n) scan that became
O(n log n) because of an accidental sort — would not be caught by the
test suite. The 80% coverage threshold rewards behavioral coverage,
not algorithmic complexity.

The closest available signal is the `duration` field on each
`HistoryItem`; a future CI pass could run a fixed benchmark on a
synthetic dataset and assert against a budget. Today it doesn't.

### 2. Worker-spawn cost is not measured in CI

`@vitest/web-worker` runs workers in-process, so the spawn-overhead
benchmark is not realistic in the test environment. The calibration
unit tests assert math, not cost. Real-world spawn behavior is
verified only through the consumer.

### 3. `package.json` dependencies vs devDependencies are inverted

`vite` is listed under `dependencies`, but it's a build tool. This is
either a real intentional choice (so consumers can compose the worker
loader themselves) or an oversight; it would benefit from clarification
in the README or being moved to `peerDependencies`. The current shape
works because consumers also use Vite, so no one's classpath gets two
copies.

### 4. The `notifications` (Snackbar) helper depends on the DOM

`Snackbar` is exported as a utility but assumes a browser DOM. Non-
browser consumers (Node / Pyodide) cannot use it; it should arguably
move to a sub-export so its DOM dependency is opt-in.

### 5. Some types duplicate `@hydroserver/client`

`Thing`, `Datastream`, `Workspace`, etc., are defined in `src/types/`.
The qc-app uses `@hydroserver/client`'s versions in the consumer code
and only uses qc-utils' shapes inside the QC engine surface. For new
consumers, the qc-utils copies are sufficient but slightly behind
`@hydroserver/client`. A future cleanup should pick one source of
truth.

### 6. `vue-tsc` is the type emitter for a Vue-free package

`npm run build` runs `vue-tsc --declaration --emitDeclarationOnly`.
`vue-tsc` is just `tsc` with Vue SFC support; in this package it's
identical to `tsc`. It's a leftover habit from when the build script
was copied from the qc-app. Swapping to plain `tsc` would shave a
small build cost and reduce surprise; it's not a behavior change.

### 7. `Snackbar` is still a top-level export

`Snackbar` lives in `utils/notifications.ts` and is exported from the
package root. The qc-app uses it, so it's not dead weight — but it's
the only DOM-dependent symbol in an otherwise headless library. See
item 4 for the consequence; a sub-export (`@uwrl/qc-utils/notifications`)
is the obvious next step if/when a non-browser consumer appears.

## Dependency management

- **Dependabot** is enabled (`.github/dependabot.yml`); a
  `dependabot-reviewer.yml` workflow auto-approves trivial bumps after
  CI.
- **Major bumps** are run manually via `npm run up` (taze).
- Hot upgrade vectors:
  - `vite` (build tool — major bumps may need config edits).
  - `vitest` + `@vitest/coverage-v8` + `@vitest/web-worker` (must
    stay version-aligned).
  - `typescript` (`latest` in package.json — pinning when stable
    would help reproducibility).

## Where the code is solid

- The dispatch surface is small (`dispatch`, `dispatchAction`,
  `dispatchFilter`, `undo`, `redo`, `reload`, `reloadHistory`,
  `removeHistoryItem`) and consistently the only mutation path. No
  sneaky escape hatches.
- The two-flavor kernel pattern is consistent across every op. Reading
  one is enough to understand all of them.
- `serializeHistory` / `parseHistory` / `applyHistory` form a clean
  round-trip with explicit version handling.
- Calibration is opt-in and degrades gracefully; first-session
  fallback profile is intentionally conservative.
- Worker / inline routing (and dataset / selection sizes, timing,
  status) is observable via the per-entry `HistoryItem.execution`
  record. The qc-app surfaces the mode as a dev-mode badge —
  concrete, per-call signal.

## See also

- [TESTING.md](./TESTING.md) — how to run, write, and debug tests
- [README](../README.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [API_REFERENCE.md](./API_REFERENCE.md)
- [ONBOARDING.md](./ONBOARDING.md) — documentation gaps
- [PERFORMANCE.md](./PERFORMANCE.md)
- [CALIBRATION.md](./CALIBRATION.md)
- [QC_HISTORY.md](./QC_HISTORY.md)
