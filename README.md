# HydroServer Quality Control App

This web app facilitates QC/QA for time series observations stored in a HydroServer database instance. It features a multi-axis plot for visually overlaying datastreams and includes QC tools such as linear drift correction and interpolation.

[Documentation](https://hydroserver2.github.io/hydroserver/)

[Contributing](https://github.com/hydroserver2/hydroserver/blob/main/CONTRIBUTING.md)

[Issue Tracker](https://github.com/hydroserver2/hydroserver/issues)

[License](LICENSE)

## E2E Tests

Playwright end-to-end tests cover the QC golden path: load a datastream, apply a filter, apply an edit, and submit the quality-controlled observations.

One-time setup (run from inside `hydroserver-qc-app/`):

```bash
npm install
npx playwright install chromium firefox
```

Run modes:

```bash
# Headed — opens a visible browser; useful for local debugging.
npm run test:e2e

# Headless — the mode CI uses; also handy for fast local runs.
npm run test:e2e:ci

# Golden path tests against playground instance.
npm run test:e2e:live
```

Browser matrix: **chromium** and **firefox**. WebKit is intentionally excluded because `SharedArrayBuffer` + COOP/COEP behavior differs in Safari and needs separate validation.

Dev server: Playwright's `webServer` config auto-starts the Vite dev server and targets `http://127.0.0.1:1203`. Locally `reuseExistingServer: true`, so if you already have `npm run dev` running Playwright reuses it; in CI a fresh server is always launched. The Vite dev server sets the `Cross-Origin-Opener-Policy` and `Cross-Origin-Embedder-Policy` headers that `SharedArrayBuffer` (used by the plotting and edit workers in `@uwrl/qc-utils`) requires — which is why the suite runs against the dev server rather than a plain `file://` page or a static preview.

Backend dependency: the smoke spec currently runs against the live `playground.hydroserver.org` backend configured via `.env.local` (`VITE_APP_API_URL`, `VITE_APP_HS_USER`, `VITE_APP_HS_PW`). Point `.env.local` at a reachable HydroServer instance with valid credentials before running the suite.

Specs live in `hydroserver-qc-app/e2e/` (separate from Vitest unit specs under `src/**/__tests__/`).

## Funding and Acknowledgements

Funding for this project was provided by the National Oceanic & Atmospheric Administration (NOAA), awarded to the Cooperative Institute for Research to Operations in Hydrology (CIROH) through the NOAA Cooperative Agreement with The University of Alabama (NA22NWS4320003).
