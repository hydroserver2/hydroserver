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
  managedDatastream,
  processingLevels,
  QC_SESSION_AUTHOR,
  QC_SOURCE_CHECKSUM,
  datastreamStatuses,
  qcHistories,
  qcSessions,
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
  /**
   * Seed the fixture's committed session over the whole observation window.
   * Defaults to true; turn it off for a history with nothing committed.
   */
  qcCommittedSession?: boolean
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
  createdBy?: { name: string; email: string }
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
    'Access-Control-Expose-Headers': 'X-Checksum',
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

/**
 * Pagination meta for a list response that always returns everything in one
 * shot. The limit is one more than the count, so the client's pager sees a
 * short page and doesn't ask for the next one (these routes ignore `offset`).
 */
function listMeta(count: number) {
  return { offset: 0, limit: count + 1, numberMatched: count, numberReturned: count }
}

/**
 * A single-item response. The API always sends `included` (null unless asked
 * for), and the client only unwraps `data` from a body that has it.
 */
function item(data: unknown, included: unknown = null) {
  return { data, included, links: [] }
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
  if (withQcHistories && options.qcCommittedSession !== false) {
    sessionState.push(...qcSessions.map((s) => ({ ...s, operations: [] })))
  }
  // The managed datastream only exists for specs that opted into histories.
  const overrides = options.catalogOverrides ?? {}
  const catalog = (
    withQcHistories ? [...datastreams, managedDatastream] : datastreams
  ).map((ds) => ({ ...ds, ...overrides[ds.id] }))
  const catalogIncluded = {
    workspaces,
    monitoringSites,
    methods,
    observedProperties,
    processingLevels,
    units,
  }
  // What the app creates, so reading it back after a create finds it.
  const createdHistories: Array<Record<string, any>> = []
  const createdDatastreams: Array<Record<string, any>> = []

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
    // Same restructuring: GET /observations?datastreamId={id}, not nested
    // under /datastreams/{id}/observations.
    const obsList = path === '/api/ogc/collections/observations/items'
    if (obsList && method === 'GET') {
      const params = new URL(url).searchParams
      const dsId = params.get('datastreamId') ?? ''
      const series = observationsById[dsId] ?? observations
      // Honour the `datetime` interval the client always sends. Without
      // this, the app's cache-extension logic in `fetchObservationsInRange`
      // (which re-fetches the segment outside its cached window every time
      // the range moves) would receive the full fixture series on
      // each call and stack duplicates into the ObservationRecord,
      // visible as wrong point counts and a long phantom line
      // connecting the first and last observations.
      const [tMin, tMax] = parseDatetimeInterval(params.get('datetime'))
      const sliced =
        tMin == null && tMax == null ? series : sliceSeries(series, tMin, tMax)
      // Only the first page carries data, so the client's paging stops after it.
      const offset = Number(params.get('offset') ?? 0)
      const groups =
        offset > 0 || !sliced.result.length ? [] : [{ datastreamId: dsId, columns: sliced }]
      // Every mocked session starts from this checksum, so the source never changes.
      return json(
        route,
        { data: groups, meta: listMeta(sliced.result.length) },
        200,
        { 'X-Checksum': QC_SOURCE_CHECKSUM }
      )
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

    // --- Quality-control histories / sessions / operations ---
    // Served ahead of the single-history route, which would otherwise match
    // the start of every session path.
    const qcSessionRoute = path.match(
      /\/api\/ogc\/collections\/quality-control-histories\/items\/([^/]+)\/sessions(?:\/([^/]+)(?:\/(commit|operations)(?:\/([^/]+))?)?)?$/
    )
    if (qcSessionRoute) {
      return handleQcSessions(route, sessionState, qcSessionRoute)
    }
    const historyGet = path.match(
      /\/api\/ogc\/collections\/quality-control-histories\/items\/([^/]+)$/
    )
    if (historyGet && method === 'GET') {
      const history = [...qcHistories, ...createdHistories].find(
        (h) => h.id === historyGet[1]
      )
      if (!history) return json(route, { detail: 'History not found.' }, 404)
      return json(route, item(history))
    }
    if (path.endsWith('/api/ogc/collections/quality-control-histories/items')) {
      if (method === 'POST') {
        const body = await safeJson(request)
        createdHistories.push({ ...body, id: 'qch-e2e-new' })
        return json(route, { id: 'qch-e2e-new' }, 201)
      }
      const histories = withQcHistories ? qcHistories : []
      return json(route, { data: histories, meta: listMeta(histories.length) })
    }

    // --- Monitoring sites / datastreams / processing levels / observed properties ---
    if (path.endsWith('/api/ogc/collections/monitoring-sites/items') && method === 'GET') {
      return json(route, { data: monitoringSites, meta: listMeta(monitoringSites.length) })
    }
    if (path.endsWith('/api/ogc/collections/datastreams/items')) {
      if (method === 'POST') {
        const body = await safeJson(request)
        datastreamCreates.push(body)
        // The API answers with the new id; the client then reads the
        // datastream back, which the single-datastream route serves.
        createdDatastreams.push({ ...body, id: 'ds-qc-e2e-created' })
        return json(route, { id: 'ds-qc-e2e-created' }, 201)
      }
      return json(route, {
        data: catalog,
        meta: listMeta(catalog.length),
        included: catalogIncluded,
      })
    }
    if (path.endsWith('/api/ogc/collections/datastream-statuses/items') && method === 'GET') {
      return json(route, { data: datastreamStatuses, meta: listMeta(datastreamStatuses.length) })
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
      const ds =
        [...catalog, ...createdDatastreams].find((d) => d.id === id) ?? catalog[0]
      return json(route, item(ds, catalogIncluded))
    }

    // --- Tags / attachments / other sub-resources the app may touch
    //     in DatastreamInformationCard: return empty arrays so the
    //     UI renders without errors.
    if (path.includes('/attachments')) {
      return json(route, { data: [], meta: listMeta(0) })
    }

    // Catch-all: return an empty list so unexpected endpoints don't
    // 404 and trigger console noise that masks real failures.
    return json(route, { data: [], meta: listMeta(0) })
  })
}

/**
 * Stateful stand-in for the QC session and operation endpoints, covering
 * what the editor calls to start, save, commit, and delete a session. It
 * refuses what the API refuses, so a test can't pass on a request the real
 * server would reject.
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
  const refuse = (detail: string) => json(route, { detail }, 400)
  const inHistory = state.filter((s) => s.historyId === historyId)
  // Sessions are served without operations, which have their own route.
  const withoutOperations = ({ operations: _ops, ...rest }: MockQcSession) => rest

  if (!sessionId) {
    if (method === 'GET') {
      const params = new URL(request.url()).searchParams
      const status = params.get('status')
      const ancestorOf = params.get('ancestorOf')
      const ancestors = ancestorOf ? ancestorIds(inHistory, ancestorOf) : null
      const matched = inHistory
        .filter(
          (s) =>
            (!status || s.status === status) && (!ancestors || ancestors.has(s.id))
        )
        .map(withoutOperations)
      return json(route, { data: matched, meta: listMeta(matched.length) })
    }
    if (method === 'POST') {
      if (inHistory.some((s) => s.status === 'in_progress')) {
        return refuse('This history already has an in-progress session.')
      }
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
        // Like the API: every committed session the new window overlaps.
        dependencyIds: inHistory
          .filter(
            (s) =>
              s.status === 'committed' &&
              s.phenomenonTimeStart < body?.phenomenonTimeEnd &&
              s.phenomenonTimeEnd > body?.phenomenonTimeStart
          )
          .map((s) => s.id),
        operations: [],
      }
      state.push(session)
      return json(route, { id: session.id }, 201)
    }
  }

  const session = state.find(
    (s) => s.id === sessionId && s.historyId === historyId
  )
  if (!session) return json(route, { detail: 'Session not found.' }, 404)
  const inProgress = session.status === 'in_progress'

  if (action === 'commit' && method === 'POST') {
    if (!inProgress) return refuse('Only in-progress sessions can be committed.')
    session.status = 'committed'
    session.committedAt = now
    return noContent()
  }

  if (action === 'operations' && !operationId) {
    if (method === 'GET') {
      const ops = [...session.operations].sort((a, b) => a.order - b.order)
      return json(route, { data: ops, meta: listMeta(ops.length) })
    }
    if (method === 'POST') {
      if (!inProgress) {
        return refuse('Operations can only be added to an in-progress session.')
      }
      const bodies = ((await safeJson(request)) ?? []) as Array<
        Omit<MockQcOperation, 'id' | 'createdAt'>
      >
      const created = bodies.map((b) => ({
        ...b,
        id: `${session.id}-op-${b.order}`,
        createdAt: now,
        createdBy: QC_SESSION_AUTHOR,
      }))
      session.operations.push(...created)
      return json(route, created.map(({ id }) => ({ id })), 201)
    }
  }

  if (action === 'operations' && operationId) {
    const index = session.operations.findIndex((o) => o.id === operationId)
    if (index < 0) return json(route, { detail: 'Operation not found.' }, 404)
    if ((method === 'PATCH' || method === 'DELETE') && !inProgress) {
      return refuse('Operations can only be changed in an in-progress session.')
    }
    if (method === 'PATCH') {
      const body = await safeJson(request)
      session.operations[index]!.comment = body?.comment ?? null
      return noContent()
    }
    if (method === 'DELETE') {
      session.operations.splice(index, 1)
      return noContent()
    }
  }

  if (!action) {
    if (method === 'GET') return json(route, item(withoutOperations(session)))
    if (method === 'PATCH') {
      if (!inProgress) return refuse('Only in-progress sessions can be updated.')
      const body = await safeJson(request)
      if (body && 'description' in body) session.description = body.description
      return noContent()
    }
    if (method === 'DELETE') {
      if (!inProgress) return refuse('Only in-progress sessions can be deleted.')
      state.splice(state.indexOf(session), 1)
      return noContent()
    }
  }

  return json(route, { detail: `Unmocked ${method} ${pathOf(request.url())}` }, 405)
}

/** Every session `id` depends on, directly or through others. */
function ancestorIds(sessions: MockQcSession[], id: string): Set<string> {
  const found = new Set<string>()
  const frontier = [id]
  while (frontier.length) {
    const s = sessions.find((x) => x.id === frontier.pop())
    for (const dep of s?.dependencyIds ?? []) {
      if (!found.has(dep)) {
        found.add(dep)
        frontier.push(dep)
      }
    }
  }
  return found
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
