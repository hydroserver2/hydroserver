/**
 * Route-level HydroServer mocks for Playwright.
 *
 * The real QC app talks to a HydroServer instance (`/api/data/*` and
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
 * The handlers match on path fragments (`/api/data/datastreams/...`)
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
  managedDatastream,
  processingLevels,
  QC_SESSION_AUTHOR,
  QC_SOURCE_CHECKSUM,
  datastreamStatuses,
  qcHistories,
  qcSessions,
  resultQualifiers,
  sensors,
  session,
  things,
  units,
  workspaces,
} from './fixtures'

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
   * Field overrides for catalog datastreams, keyed by id. Lets a spec move a
   * datastream's phenomenon times to match a custom observation series.
   */
  catalogOverrides?: Record<string, Record<string, unknown>>
  /**
   * Accumulates every bulk-create submission the app makes while the
   * mocks are active. Consumers can assert on request ordering /
   * payload contents without installing a second route handler.
   */
  submissions?: Array<{ mode: string | null; body: any }>
  /**
   * Accumulates every datastream create body the app posts, so a spec can
   * assert on what the create-datastream form sent.
   */
  datastreamCreates?: Array<Record<string, any>>
  /**
   * Serve the QC history fixture, so `DATASTREAM_ID` has a managed
   * datastream derived from it. Off by default: most specs want a catalog
   * where every row plots straight from its check box.
   */
  qcHistories?: boolean
  /**
   * Live QC session state, seeded from the session fixtures when
   * `qcHistories` is on. The handlers create, save, and commit sessions in
   * it, so pass an array to assert on what the app persisted.
   */
  qcSessionState?: MockQcSession[]
  /** Set to false to mark the session as unauthenticated. */
  authenticated?: boolean
}

export interface MockQcOperation {
  id: string
  operationType: string
  arguments: unknown
  comment?: string | null
  order: number
  createdAt: string
}

export interface MockQcSession {
  id: string
  historyId: string
  status: 'in_progress' | 'committed'
  description: string | null
  phenomenonTimeStart: string
  phenomenonTimeEnd: string
  sourceChecksum: string
  createdAt: string
  committedAt: string | null
  createdBy: { name: string; email: string }
  dependencyIds: string[]
  operations: MockQcOperation[]
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
      'X-Total-Pages': '1',
      ...extraHeaders,
    },
    body: JSON.stringify(body),
  })
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
  const datastreamCreates = options.datastreamCreates ?? []
  const withQcHistories = options.qcHistories ?? false
  const sessionState = options.qcSessionState ?? []
  if (withQcHistories) {
    sessionState.push(...qcSessions.map((s) => ({ ...s, operations: [] })))
  }
  // The managed datastream only exists for specs that opted into histories.
  const overrides = options.catalogOverrides ?? {}
  const catalog = (
    withQcHistories ? [...datastreams, managedDatastream] : datastreams
  ).map((ds) => ({ ...ds, ...overrides[ds.id] }))

  // Match only real HydroServer API calls by pathname. A bare `**/api/**`
  // glob also catches the dev server's own source modules. The QC app
  // aliases `@hydroserver/client` to `packages/hydroserver-ts/src`, whose
  // files live under `.../src/api/...` and are served from
  // `/qc/@fs/.../src/api/runtime.ts`. Those URLs contain `/api/` but their
  // pathname starts with `/qc/`, so intercepting them would return
  // `application/json` for a module script and blank the app. Real API
  // requests always have a pathname that starts with `/api/`.
  const isApiRequest = (url: URL): boolean => url.pathname.startsWith('/api/')

  // Preflights for anything: the real server serves OPTIONS via
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
      // Any other auth endpoint (providers, redirects): return OK.
      return json(route, { status: 200, data: {}, meta: { is_authenticated: authenticated } })
    }

    // --- Bulk observation create (submit) ---
    const bulkCreate = path.match(/\/api\/data\/datastreams\/([^/]+)\/observations\/bulk-create/)
    if (bulkCreate && method === 'POST') {
      const params = new URL(url).searchParams
      const body = await safeJson(request)
      submissions.push({ mode: params.get('mode'), body })
      return json(route, { data: { created: (body?.data ?? []).length } }, 200)
    }

    // --- Observations list (columnar) ---
    const obsList = path.match(/\/api\/data\/datastreams\/([^/]+)\/observations$/)
    if (obsList && method === 'GET') {
      const dsId = obsList[1]
      const params = new URL(url).searchParams
      const page = Number(params.get('page') ?? '1')
      const series = observationsById[dsId] ?? observations
      // Honour the `phenomenon_time_min` / `phenomenon_time_max`
      // params the client always sends. Without this, the app's
      // cache-extension logic in `fetchObservationsInRange` (which
      // re-fetches the segment outside its cached window every time
      // the range moves) would receive the full fixture series on
      // each call and stack duplicates into the ObservationRecord,
      // visible as wrong point counts and a long phantom line
      // connecting the first and last observations.
      const tMin = parseISOorNull(params.get('phenomenon_time_min'))
      const tMax = parseISOorNull(params.get('phenomenon_time_max'))
      const sliced =
        tMin == null && tMax == null ? series : sliceSeries(series, tMin, tMax)
      // Only the first page carries data; subsequent pages are empty
      // so the client's pagination loop terminates.
      const data = page === 1 ? sliced : { phenomenonTime: [], result: [] }
      return json(route, { data }, 200, { 'X-Total-Pages': '1' })
    }

    // --- Units ---
    const unitGet = path.match(/\/api\/data\/units\/([^/]+)$/)
    if (unitGet && method === 'GET') {
      const id = unitGet[1]
      const unit = units.find((u) => u.id === id) ?? units[0]
      return json(route, { data: unit })
    }
    if (path.endsWith('/api/data/units') && method === 'GET') {
      return json(route, { data: units })
    }

    // --- Workspaces ---
    if (path.endsWith('/api/data/workspaces') && method === 'GET') {
      return json(route, { data: workspaces })
    }

    // --- Quality-control histories / sessions / operations ---
    // Served ahead of the datastream routes: the history paths sit under
    // the same `/api/data` prefix and would otherwise fall to the
    // empty-list catch-all.
    const qcSessionRoute = path.match(
      /\/api\/data\/quality-control\/histories\/([^/]+)\/sessions(?:\/([^/]+)(?:\/(commit|operations)(?:\/([^/]+))?)?)?$/
    )
    if (qcSessionRoute) {
      return handleQcSessions(route, sessionState, qcSessionRoute)
    }
    if (path.endsWith('/api/data/quality-control/histories')) {
      if (method === 'POST') {
        const body = await safeJson(request)
        return json(
          route,
          { data: { id: 'qch-e2e-new', ...body } },
          201
        )
      }
      return json(route, { data: withQcHistories ? qcHistories : [] })
    }

    // --- Things / datastreams / processing levels / observed properties ---
    if (path.endsWith('/api/data/things') && method === 'GET') {
      return json(route, { data: things })
    }
    if (path.endsWith('/api/data/datastreams')) {
      if (method === 'POST') {
        const body = await safeJson(request)
        datastreamCreates.push(body)
        // Echo the body back the way the server does, with an assigned id
        // and the nested relations `expand_related: true` asks for.
        const created = { ...body, id: 'ds-qc-e2e-created' }
        return json(
          route,
          {
            data: {
              ...created,
              thing: things.find((t) => t.id === created.thingId),
              unit: units.find((u) => u.id === created.unitId),
              sensor: sensors.find((s) => s.id === created.sensorId),
              observedProperty: observedProperties.find(
                (o) => o.id === created.observedPropertyId
              ),
              processingLevel: processingLevels.find(
                (p) => p.id === created.processingLevelId
              ),
            },
          },
          201
        )
      }
      return json(route, { data: catalog })
    }
    // Ahead of the single-datastream route, which would otherwise treat
    // "statuses" as a datastream id.
    if (path.endsWith('/api/data/datastreams/statuses') && method === 'GET') {
      return json(route, { data: datastreamStatuses })
    }
    if (path.endsWith('/api/data/processing-levels') && method === 'GET') {
      return json(route, { data: processingLevels })
    }
    if (path.endsWith('/api/data/observed-properties') && method === 'GET') {
      return json(route, { data: observedProperties })
    }
    if (path.endsWith('/api/data/sensors') && method === 'GET') {
      return json(route, { data: sensors })
    }
    if (path.endsWith('/api/data/result-qualifiers') && method === 'GET') {
      return json(route, { data: resultQualifiers })
    }

    // --- Single datastream ---
    const dsGet = path.match(/\/api\/data\/datastreams\/([^/]+)$/)
    if (dsGet && method === 'GET') {
      const id = dsGet[1]
      const ds = catalog.find((d) => d.id === id) ?? catalog[0]
      return json(route, { data: ds })
    }

    // --- Tags / attachments / other sub-resources the app may touch
    //     in DatastreamInformationCard: return empty arrays so the
    //     UI renders without errors.
    if (path.includes('/tags') || path.includes('/attachments')) {
      return json(route, { data: [] })
    }

    // Catch-all: return an empty list so unexpected endpoints don't
    // 404 and trigger console noise that masks real failures.
    return json(route, { data: [] })
  })
}

/**
 * Stateful stand-in for the QC session and operation endpoints, covering
 * what the editor calls to start, save, commit, and delete a session.
 */
async function handleQcSessions(
  route: Route,
  state: MockQcSession[],
  [, historyId, sessionId, action, operationId]: RegExpMatchArray
): Promise<void> {
  const request = route.request()
  const method = request.method()
  const now = new Date().toISOString()
  const noContent = () =>
    route.fulfill({ status: 204, headers: corsHeaders(route) })

  if (!sessionId) {
    if (method === 'GET') {
      const status = new URL(request.url()).searchParams.get('status')
      return json(route, {
        data: state.filter(
          (s) => s.historyId === historyId && (!status || s.status === status)
        ),
      })
    }
    if (method === 'POST') {
      const body = await safeJson(request)
      const session: MockQcSession = {
        id: `qcs-e2e-new-${state.length + 1}`,
        historyId: historyId!,
        status: 'in_progress',
        description: body?.description ?? null,
        phenomenonTimeStart: body?.phenomenonTimeStart,
        phenomenonTimeEnd: body?.phenomenonTimeEnd,
        sourceChecksum: QC_SOURCE_CHECKSUM,
        createdAt: now,
        committedAt: null,
        createdBy: QC_SESSION_AUTHOR,
        dependencyIds: [],
        operations: [],
      }
      state.push(session)
      return json(route, { data: session }, 201)
    }
  }

  const session = state.find(
    (s) => s.id === sessionId && s.historyId === historyId
  )
  if (!session) return json(route, { detail: 'Session not found.' }, 404)

  if (action === 'commit' && method === 'POST') {
    session.status = 'committed'
    session.committedAt = now
    return json(route, { data: session })
  }

  if (action === 'operations' && !operationId) {
    if (method === 'GET') return json(route, { data: session.operations })
    if (method === 'POST') {
      const bodies = ((await safeJson(request)) ?? []) as Array<
        Omit<MockQcOperation, 'id' | 'createdAt'>
      >
      const created = bodies.map((b) => ({
        ...b,
        id: `${session.id}-op-${b.order}`,
        createdAt: now,
      }))
      session.operations.push(...created)
      return json(route, { data: created }, 201)
    }
  }

  if (action === 'operations' && operationId) {
    const index = session.operations.findIndex((o) => o.id === operationId)
    if (index < 0) return json(route, { detail: 'Operation not found.' }, 404)
    if (method === 'PATCH') {
      const body = await safeJson(request)
      session.operations[index]!.comment = body?.comment ?? null
      return json(route, { data: session.operations[index] })
    }
    if (method === 'DELETE') {
      session.operations.splice(index, 1)
      return noContent()
    }
  }

  if (!action) {
    if (method === 'GET') return json(route, { data: session })
    if (method === 'PATCH') {
      const body = await safeJson(request)
      if (body && 'description' in body) session.description = body.description
      return json(route, { data: session })
    }
    if (method === 'DELETE') {
      state.splice(state.indexOf(session), 1)
      return noContent()
    }
  }

  return json(route, { detail: `Unmocked ${method} ${pathOf(request.url())}` }, 405)
}

async function safeJson(request: ReturnType<Page['request']> | any): Promise<any> {
  try {
    return JSON.parse(request.postData() ?? 'null')
  } catch {
    return null
  }
}

function parseISOorNull(value: string | null): number | null {
  if (!value) return null
  const t = Date.parse(value)
  return Number.isFinite(t) ? t : null
}

/**
 * Mirror the real backend's `phenomenon_time_min` / `phenomenon_time_max`
 * filtering. Bounds are inclusive on both ends, matching how the QC
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
