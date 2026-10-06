/**
 * Route-level HydroServer mocks for Playwright.
 *
 * The real QC app talks to a HydroServer instance (`/api/ogc/*` and
 * `/api/auth/*`). For e2e specs we don't want to depend on a live
 * backend: tests are slow, flaky, and can't set up the exact dataset
 * shape each spec needs. This module registers `page.route()` handlers
 * that serve fixture JSON synchronously on the dev server's side.
 *
 * Usage:
 *   import { installMocks } from './support/mocks'
 *   await installMocks(page)
 *   await page.goto('/')
 *
 * The handlers match on path fragments (`/api/ogc/collections/datastreams/items/...`)
 * regardless of host.
 */

import type { Page, Route } from '@playwright/test'
import {
  DATASTREAM_ID,
  UNIT_ID,
  WORKSPACE_ID,
  buildObservations,
  datastreams,
  observedProperties,
  processingLevels,
  resultQualifiers,
  methods,
  session,
  monitoringSites,
  units,
  workspaces,
} from './fixtures'

const appHost = process.env.E2E_APP_HOST || '127.0.0.1'
const appPort = process.env.E2E_APP_PORT || '15173'
const appOrigin = `http://${appHost}:${appPort}`

export interface MockOptions {
  /**
   * Override the observation payload for the primary test datastream
   * (`DATASTREAM_ID`). Pass a factory so each spec can size / shape its
   * series; if omitted, a 120-point sine wave is served.
   */
  observations?: { phenomenonTime: string[]; result: number[] }
  /**
   * Per-datastream-id observation override. Lets multi-datastream
   * specs serve a distinct series for each plotted datastream
   * without having to install a second mocks layer. Falls back to
   * `observations` (then `buildObservations()`) for any id not
   * listed here.
   */
  observationsById?: Record<
    string,
    { phenomenonTime: string[]; result: number[] }
  >
  /**
   * Accumulates every bulk-create submission the app makes while the
   * mocks are active. Consumers can assert on request ordering /
   * payload contents without installing a second route handler.
   */
  submissions?: Array<{ mode: string | null; body: any }>
  /** Set to false to mark the session as unauthenticated. */
  authenticated?: boolean
}

function corsHeaders(route: Route): Record<string, string> {
  // The HydroServer client sends requests with `credentials: 'include'`.
  // Browsers reject `Access-Control-Allow-Origin: *` for credentialed
  // requests, so echo the request origin instead.
  const origin = route.request().headers()['origin'] ?? '*'
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Methods': 'GET,POST,PATCH,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Expose-Headers': 'X-Total-Pages,X-Total-Count',
  }
}

function json(route: Route, body: unknown, status = 200, extraHeaders: Record<string, string> = {}) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    headers: {
      ...corsHeaders(route),
      ...extraHeaders,
    },
    body: JSON.stringify(body),
  })
}

/** Pagination meta for a list response that always returns everything in one shot. */
function listMeta(count: number) {
  return { limit: count || 1, offset: 0, totalCount: count }
}

/** Convenience: derives the path portion of the requested URL. */
function pathOf(url: string): string {
  try {
    return new URL(url).pathname
  } catch {
    return url
  }
}

export async function installMocks(
  page: Page,
  options: MockOptions = {}
): Promise<void> {
  const authenticated = options.authenticated ?? true
  const observations = options.observations ?? buildObservations()
  const observationsById = options.observationsById ?? {}
  const submissions = options.submissions ?? []

  // Session authentication is now read synchronously from the
  // server-rendered `current-user` script tag. Vite serves a static shell in
  // e2e, so mirror Django's shell by adding that tag before the application
  // module runs.
  await page.route(
    (url) =>
      url.origin === appOrigin &&
      (url.pathname === '/' || url.pathname === '/qc/'),
    async (route) => {
      const response = await route.fetch()
      let body = await response.text()
      if (authenticated) {
        const currentUser = JSON.stringify(session.data.user).replaceAll(
          '<',
          '\\u003c'
        )
        body = body.replace(
          '</head>',
          `<script id="current-user" type="application/json">${currentUser}</script></head>`
        )
      }
      return route.fulfill({ response, body })
    }
  )

  // Match only real HydroServer API calls by pathname. A bare `**/api/**`
  // glob also catches the dev server's own source modules — the QC app
  // aliases `@hydroserver/client` to `packages/hydroserver-ts/src`, whose
  // files live under `.../src/api/...` and are served from
  // `/qc/@fs/.../src/api/runtime.ts`. Those URLs contain `/api/` but their
  // pathname starts with `/qc/`, so intercepting them would return
  // `application/json` for a module script and blank the app. Real API
  // requests always have a pathname that starts with `/api/`.
  const isApiRequest = (url: URL): boolean => url.pathname.startsWith('/api/')

  // Preflights for anything — the real server serves OPTIONS via
  // middleware; swallowing them here keeps the mocks happy.
  await page.route(isApiRequest, async (route) => {
    const request = route.request()
    if (request.method() === 'OPTIONS') {
      return route.fulfill({ status: 204, headers: corsHeaders(route) })
    }

    const url = request.url()
    const path = pathOf(url)
    const method = request.method()

    // --- Session / auth ---
    if (path.endsWith('/api/auth/browser/session')) {
      return json(route, {
        status: 200,
        data: session.data,
        meta: {
          is_authenticated: authenticated,
          session_token: authenticated ? session.meta.session_token : null,
        },
      })
    }
    if (path.includes('/api/auth/')) {
      // Any other auth endpoint (providers, redirects) — return OK.
      return json(route, { status: 200, data: {}, meta: { is_authenticated: authenticated } })
    }

    // --- Bulk observation create (submit) ---
    // Observations moved to a top-level resource: POST /collections/observations/bulk-create
    // with datastreamId in the body, not the path.
    const bulkCreate = path === '/api/ogc/collections/observations/bulk-create'
    if (bulkCreate && method === 'POST') {
      const params = new URL(url).searchParams
      const body = await safeJson(request)
      submissions.push({ mode: params.get('mode'), body })
      return json(route, { data: { created: (body?.data ?? []).length } }, 200)
    }

    // --- Observations list (columnar) ---
    // Same restructuring: GET /observations?datastream_id={id}, not nested
    // under /datastreams/{id}/observations.
    const obsList = path === '/api/ogc/collections/observations/items'
    if (obsList && method === 'GET') {
      const params = new URL(url).searchParams
      const dsId = params.get('datastream_id') ?? ''
      const series = observationsById[dsId] ?? observations
      // Honour the `datetime` interval the client always sends. Without
      // this, the app's cache-extension logic in `fetchObservationsInRange`
      // (which re-fetches the segment outside its cached window every time
      // the range moves) would receive the full fixture series on
      // each call and stack duplicates into the ObservationRecord —
      // visible as wrong point counts and a long phantom line
      // connecting the first and last observations.
      const [tMin, tMax] = parseDatetimeInterval(params.get('datetime'))
      const sliced =
        tMin == null && tMax == null ? series : sliceSeries(series, tMin, tMax)
      // The columnar format spreads its fields at the top level (no `data`
      // wrapper) — the fixtures are always small enough that a single
      // response covers everything, so `meta.totalCount` matching what's
      // returned here means the client never requests a second page.
      return json(route, { ...sliced, meta: listMeta(sliced.result.length) })
    }

    // --- Units ---
    const unitGet = path.match(/\/api\/ogc\/collections\/units\/items\/([^/]+)$/)
    if (unitGet && method === 'GET') {
      const id = unitGet[1]
      const unit = units.find((u) => u.id === id) ?? units[0]
      return json(route, unit)
    }
    if (path.endsWith('/api/ogc/collections/units/items') && method === 'GET') {
      return json(route, { data: units, meta: listMeta(units.length) })
    }

    // --- Workspaces ---
    if (path.endsWith('/api/ogc/collections/workspaces/items') && method === 'GET') {
      return json(route, { data: workspaces, meta: listMeta(workspaces.length) })
    }

    // --- Monitoring sites / datastreams / processing levels / observed properties ---
    if (path.endsWith('/api/ogc/collections/monitoring-sites/items') && method === 'GET') {
      return json(route, { data: monitoringSites, meta: listMeta(monitoringSites.length) })
    }
    if (path.endsWith('/api/ogc/collections/datastreams/items') && method === 'GET') {
      return json(route, {
        data: datastreams,
        meta: listMeta(datastreams.length),
        included: {
          workspaces,
          monitoringSites,
          methods,
          observedProperties,
          processingLevels,
          units,
        },
      })
    }
    if (path.endsWith('/api/ogc/collections/processing-levels/items') && method === 'GET') {
      return json(route, { data: processingLevels, meta: listMeta(processingLevels.length) })
    }
    if (path.endsWith('/api/ogc/collections/observed-properties/items') && method === 'GET') {
      return json(route, { data: observedProperties, meta: listMeta(observedProperties.length) })
    }
    if (path.endsWith('/api/ogc/collections/methods/items') && method === 'GET') {
      return json(route, { data: methods, meta: listMeta(methods.length) })
    }
    if (path.endsWith('/api/ogc/collections/result-qualifiers/items') && method === 'GET') {
      return json(route, { data: resultQualifiers, meta: listMeta(resultQualifiers.length) })
    }

    // --- Single datastream ---
    const dsGet = path.match(/\/api\/ogc\/collections\/datastreams\/items\/([^/]+)$/)
    if (dsGet && method === 'GET') {
      const id = dsGet[1]
      const ds = datastreams.find((d) => d.id === id) ?? datastreams[0]
      return json(route, {
        data: ds,
        included: {
          workspaces,
          monitoringSites,
          methods,
          observedProperties,
          processingLevels,
          units,
        },
      })
    }

    // --- Attachments / other sub-resources the app may touch
    //     in DatastreamInformationCard — return empty arrays so the
    //     UI renders without errors.
    if (path.includes('/attachments')) {
      return json(route, { data: [], meta: listMeta(0) })
    }

    // Catch-all: return an empty list so unexpected endpoints don't
    // 404 and trigger console noise that masks real failures.
    return json(route, { data: [], meta: listMeta(0) })
  })
}

async function safeJson(request: ReturnType<Page['request']> | any): Promise<any> {
  try {
    return JSON.parse(request.postData() ?? 'null')
  } catch {
    return null
  }
}

/** Parses a `datetime` instant or interval into [start, end] epoch ms; open ends are null. */
function parseDatetimeInterval(value: string | null): [number | null, number | null] {
  if (!value) return [null, null]
  const parseEnd = (part: string | undefined): number | null => {
    if (!part || part === '..') return null
    const t = Date.parse(part)
    return Number.isFinite(t) ? t : null
  }
  if (!value.includes('/')) {
    const instant = parseEnd(value)
    return [instant, instant]
  }
  const [start, end] = value.split('/')
  return [parseEnd(start), parseEnd(end)]
}

/**
 * Mirror the real backend's `datetime` filtering. Bounds are inclusive on both ends, matching how the QC
 * app issues its cache-extension queries.
 */
function sliceSeries(
  series: { phenomenonTime: string[]; result: number[] },
  tMin: number | null,
  tMax: number | null
): { phenomenonTime: string[]; result: number[] } {
  const phenomenonTime: string[] = []
  const result: number[] = []
  for (let i = 0; i < series.phenomenonTime.length; i++) {
    const ts = Date.parse(series.phenomenonTime[i] as string)
    if (tMin != null && ts < tMin) continue
    if (tMax != null && ts > tMax) continue
    phenomenonTime.push(series.phenomenonTime[i] as string)
    result.push(series.result[i] as number)
  }
  return { phenomenonTime, result }
}

export { DATASTREAM_ID, WORKSPACE_ID, UNIT_ID }
