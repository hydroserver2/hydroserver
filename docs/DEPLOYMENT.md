# Deployment &amp; Infrastructure

This document covers how the HydroServer QC App is deployed, what running
it independently looks like day-to-day, the observability you do (and
don't) get out of the box, and how upgrades and migrations work.

## Shape of a deployment

The QC App builds to a fully static SPA — HTML, JS, CSS, fonts, icons,
and inline worker bundles. Anything that can serve static files over
HTTPS and add a few response headers can host it. There is **no server
component, no database, and no background job** to operate alongside the
app itself; all the moving parts live in the user's browser.

A typical deployment looks like:

```
        ┌──────────┐         ┌──────────────┐         ┌──────────────────────┐
 user → │   CDN    │ ──────► │ Object store │ ──────► │   HydroServer API    │
        │ (CF/S3/  │  HTML   │ (S3 bucket   │  data   │ (Django + Postgres,  │
        │ CloudFront) │ JS/CSS  │  static SPA)  │  REST   │  operated separately)│
        └──────────┘         └──────────────┘         └──────────────────────┘
            ▲
            │ COOP / COEP headers must be set here
            │ for the SharedArrayBuffer fast path
```

Three required pieces:

1. **Static hosting** — any object store + CDN. AWS S3 + CloudFront is
   what the demo workflow uses (see below); GitHub Pages, Cloudflare
   Pages, Azure Blob + Front Door, or nginx in a container all work.
2. **A HydroServer instance to point at** — provided to the build at
   compile-time via `VITE_APP_API_URL`. The app does not bundle a default.
3. **Response headers** at the edge:
   - `Cross-Origin-Opener-Policy: same-origin`
   - `Cross-Origin-Embedder-Policy: require-corp`

   These unlock `SharedArrayBuffer` for the qc-utils worker pool. Without
   them the app still works, just slower on large edits; the worker layer
   transparently falls back to inline kernels. If your HydroServer
   deployment can't yet emit `Cross-Origin-Resource-Policy`, build with
   `VITE_APP_DISABLE_COOP=1` so the headers are dropped — otherwise the
   browser will block the API response.

## Reference deployment: AWS S3 + CloudFront

The repo ships a `workflow_dispatch` GitHub Actions workflow at
`.github/workflows/hydroserver_qc_app_demo_deployment.yaml` that builds and
deploys to AWS. The flow:

1. **Operator triggers the workflow** from the GitHub Actions UI, picking
   a GitHub Environment (which carries the AWS account / IAM role / bucket
   suffix vars) and an optional branch (default `main`).
2. **`check-environment-variables`** validates the GH Environment exposes
   `AWS_ACCOUNT_ID`, `AWS_IAM_ROLE`, `AWS_REGION`, `PROXY_BASE_URL`,
   `APP_ROUTE`. Missing any of those aborts the deploy.
3. **`verify-ci-success`** queries the GitHub API for the latest CI run
   on the chosen branch. If it didn't succeed, the deploy aborts with a
   pointer to the failing run. **You cannot deploy a branch whose CI is
   red** — by design.
4. **`deploy-hydroserver-data-mgmt-app`**:
   - Assumes the IAM role via OIDC (`aws-actions/configure-aws-credentials`).
   - Checks out the chosen branch.
   - Sets up Node 23.x with `package-lock.json` caching.
   - Generates `.env` with `VITE_APP_API_URL` (sourced from
     `PROXY_BASE_URL`), `VITE_APP_ROUTE`, and `VITE_APP_VERSION` (the
     deploy commit SHA).
   - Runs `npm install && npm ci` then `npm run build`.
   - Syncs `./dist/` to
     `s3://hydroserver-qc-demo-app-${environment}-${account}/quality-control-demo/`
     with `--delete` and copies `index.html` to both root and
     `quality-control-demo/`.
   - Looks up the matching CloudFront distribution by AWS tag
     (`hydroserver-instance: <environment>`) and issues a `/*`
     invalidation.

Operationally that means:

- **You promote a new release by merging to `main` and re-running the
  workflow.** No long-lived servers to drain or roll.
- **The CloudFront invalidation is the only "live" step.** Until it
  completes (~30-60 s typical), users may keep seeing the previous bundle
  due to edge caching. `index.html` is small; CSS/JS get content-hashed
  filenames by Vite, so they don't risk stale references.
- **Rollback is "deploy the previous tag."** There is no in-place
  rollback button. If you need to revert, re-run the workflow with the
  previous commit's branch / tag.

## Running it independently

For a self-hosted instance pointed at your own HydroServer:

```bash
# 1. Build with your config baked in
git clone https://github.com/hydroserver2/hydroserver-qc-app.git
cd hydroserver-qc-app
npm ci

cat > .env.local <<'EOF'
VITE_APP_API_URL=https://hydroserver.example.org
# Optional:
VITE_APP_VERSION=$(git describe --tags --always)
VITE_APP_GOOGLE_OAUTH_ENABLED=1
VITE_APP_DISABLE_COOP=                 # leave blank unless backend lacks CORP
EOF

npm run build                          # → dist/

# 2. Serve dist/ behind a CDN or nginx
#    Make sure the edge sets COOP/COEP headers (unless DISABLE_COOP=1).
```

Minimum viable nginx for a single-host install:

```nginx
server {
    listen 443 ssl;
    server_name qc.hydroserver.example.org;

    root /var/www/qc-app;
    index index.html;

    add_header Cross-Origin-Opener-Policy "same-origin" always;
    add_header Cross-Origin-Embedder-Policy "require-corp" always;

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

`index.html` should be served with `Cache-Control: no-cache` (or short
TTL); the content-hashed asset filenames under `assets/` can be cached
aggressively.

## Operational observability

The QC App is browser-side software, so the observability story is
"what the operator sees" + "what the backend logs":

### What you have today

- **In-app Snackbar notifications** (`Snackbar` from `qc-utils`) surface
  successes, warnings, and failures for every user-driven action — load
  failures, submit results, script import reports, etc.
- **Browser console** carries qc-utils dispatch logs and any unhandled
  promise rejections. The history panel in dev mode displays per-entry
  `inline` vs `worker` badges when `import.meta.env.DEV` is truthy.
- **HydroServer backend access logs** are the source of truth for API-
  level errors. The QC App passes user-readable error messages from
  backend responses straight to the Snackbar, so backend incidents
  surface in real time to the operator who triggered them.
- **CloudFront / nginx access logs** at the edge show 4xx/5xx rates and
  request volumes. These are the deployment's primary uptime signal.

### What you do NOT have built in

- **No application-level analytics or error reporting service** (no Sentry,
  no Datadog RUM, no Google Analytics). The team has consciously kept
  the SPA telemetry-free; adding it is an opt-in deployment decision.
- **No server-side metrics**, because there is no server-side runtime.
- **No audit log** of QC edits — the QC script file is the closest
  equivalent (export before submitting to keep a replayable record).
- **No alerting** beyond what your CDN / object-store provider offers.

If you need richer observability, the natural insertion point is `main.ts`
(client-side error reporter init) and `Snackbar` (level-aware sink).
Worker errors surface through the dispatch path, so wrapping
`ObservationRecord.dispatch` is the cleanest place to instrument timing
and failure rates.

## Version upgrades and migrations

There are three flavors of upgrade to keep separate.

### 1. App-version upgrades

The user-facing version is built into `dist/index.html` at compile time
via `VITE_APP_VERSION` and surfaced in the about menu. To upgrade an
existing deployment:

1. Merge to `main`.
2. Wait for CI to go green.
3. Re-run the deploy workflow.
4. Verify the CloudFront invalidation completes and the about-menu
   version string ticks over.

There is no client-side migration step — `localStorage` keys are kept
shape-stable. If you ever need to break a persisted shape:

- Bump a version key inside the affected store's persisted slice and
  drop the old value on rehydrate. The `qc-utils` calibration store
  uses this pattern (`qc-utils:calibration:v<n>`); copy it.
- Never silently coerce — if the persisted shape might be wrong, drop
  it and let the user re-pick their workspace / preferences. Reset is
  cheap; data corruption is not.

### 2. qc-utils version upgrades

`@uwrl/qc-utils` is the QC engine, versioned independently and published
to npm. The QC App pins it in `package.json` (`"@uwrl/qc-utils": "^0.0.x"`).
Upgrades:

```bash
npm install @uwrl/qc-utils@<version>
npm test
npm run build
# commit + deploy as a normal app release
```

The package is pre-1.0, so assume any minor bump may require code
changes in the consumer — read the qc-utils commit log and re-run E2E.

For local development against an unreleased qc-utils:

```bash
# qc-utils
npm link
npm run dev          # vite watch

# hydroserver-qc-app
npm run link-qc-utils
npm run dev
```

HMR doesn't propagate through linked packages — refresh the browser to
pick up changes. See [ONBOARDING.md](./ONBOARDING.md) for the full
linked-dev workflow.

### 3. HydroServer backend / schema migrations

These are owned by the HydroServer project, not by the QC App. What
matters here is **how the QC App weathers them**:

- The app talks to the backend over REST through `@hydroserver/client`.
  Schema changes that break the response shape will manifest as type
  errors at build time (good — won't deploy) or runtime Snackbar errors
  (bad but visible).
- The QC App pins a `@hydroserver/client` version in `package.json`. When
  the backend ships a schema change, bump the client version, run
  `npx vue-tsc --noEmit` to see the breakage, and patch the call sites.
- The observation upload path uses `mode: 'replace'` on the bulk POST.
  Replace semantics are stable across HydroServer versions — if you ever
  need to change to append-only or upsert semantics, that's a coordinated
  release between the QC App and the backend.

### Compatibility matrix

| Component                 | Pinned via             | Owned by                |
|---------------------------|------------------------|-------------------------|
| Vue / Vuetify / Pinia     | `package.json`         | This repo               |
| `@uwrl/qc-utils`          | `package.json`         | `qc-utils/` (sibling)   |
| `@hydroserver/client`     | `package.json`         | HydroServer project     |
| HydroServer REST schema   | (implicit via client)  | HydroServer project     |
| Browser baseline (SAB)    | Chrome 111+ / FF 119+ / Safari 16.4+ | Browser vendors |

## CI

`.github/workflows/ci.yml` runs on every push and PR to `main`:

1. `npx vue-tsc --noEmit` — type-check.
2. `npm run coverage` — Vitest with the 80% coverage threshold.
3. `npm run build` — production build sanity check.

Concurrency is grouped by workflow + ref with `cancel-in-progress: true`,
so pushing again kills the older run. The deploy workflow refuses to run
unless this CI is green on the chosen branch.

Dependabot is enabled (`.github/dependabot.yml`); a separate
`dependabot-reviewer.yml` workflow auto-approves trivial bumps.

## Day-2 operations checklist

- **Watching the deployment**: CloudFront 5xx rate + the HydroServer
  backend's own dashboards. The CDN never gets 5xx unless the bucket /
  origin is broken.
- **Watching user reports**: Snackbar messages quote the backend error
  text verbatim. Asking a user "what does the red banner say?" usually
  pinpoints the failure.
- **Bumping a dependency**: open the Dependabot PR, wait for CI, merge.
  Anything that touches `plotly.js`, `@uwrl/qc-utils`, or `vue` warrants
  a manual smoke test against `playground.hydroserver.org`.
- **Restoring a broken deployment**: re-run the deploy workflow against
  the last green commit / tag. There is no live state to restore.
- **Rotating credentials**: there are no app-owned credentials. The CI
  IAM role lives in the GitHub Environment; rotate it the same way you
  rotate any GH-OIDC role.

## See also

- [README](../README.md) — quick start, config keys
- [ARCHITECTURE.md](./ARCHITECTURE.md) — what's running where
- [ONBOARDING.md](./ONBOARDING.md) — first-day setup
- [PERFORMANCE.md](./PERFORMANCE.md) — what scales and what doesn't
