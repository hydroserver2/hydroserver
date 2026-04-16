# @uwrl/qc-utils

Quality-control utilities for hydrological time-series data. Used by [hydroserver-qc-app](https://github.com/hydroserver2/hydroserver-qc-app).

## Local development with `npm link`

This package is consumed by `hydroserver-qc-app` via `npm link`. For active local development:

**1. From `qc-utils/`** (this repo):

```sh
npm install
npm link            # registers @uwrl/qc-utils globally
npm run dev         # starts vite build --watch — rebuilds dist/ on every source change
```

Leave that terminal running.

**2. From `hydroserver-qc-app/`** (the consumer, in a second terminal):

```sh
npm install
npm run link-qc-utils    # symlinks node_modules/@uwrl/qc-utils → this dist/
npm run dev              # starts the Vite dev server
```

Edit any file in `qc-utils/src/`. The watcher rebuilds `dist/` within ~1s. Refresh the app browser to pick up the change.

### Caveats

- `vite build --watch` rebuilds the JS bundle but **does not emit `.d.ts` files** (those come from the full `npm run build`). If the app surfaces stale type errors during dev, run `npm run build` once in `qc-utils` and they'll refresh.
- Two terminals required (one per repo). If the friction proves real, a future phase can wire `concurrently` to run both watchers from a single command.
- HMR is **not** propagated through the linked dependency — Vite library mode doesn't expose HMR boundaries to the consumer. Browser refresh is the loop.

## Scripts

| Script | Purpose |
|--------|---------|
| `npm run dev` | Start the watch-mode bundler for linked-dev workflow (alias of `watch`). |
| `npm run watch` | Same as `dev` (kept for backward compatibility). |
| `npm run build` | Production build — bundle + emit `.d.ts` declarations. |
| `npm run test` | Run the Vitest suite once. |
| `npm run coverage` | Run the suite with v8 coverage and the 80% threshold. |
| `npm run lint` | Run ESLint over `src/`. |
| `npm run lint:fix` | Auto-fix lintable errors. |
| `npm run preview` | Preview the production build with Vite. |
| `npm link` | Register this package for `npm link @uwrl/qc-utils` in consumers. |
| `npm publish` (`pub`) | Publish to npm under `--access public`. |

## CI

GitHub Actions runs `tsc --noEmit → coverage → lint → build` on every push and PR-to-main. See `.github/workflows/ci.yml`.

## License

ISC
