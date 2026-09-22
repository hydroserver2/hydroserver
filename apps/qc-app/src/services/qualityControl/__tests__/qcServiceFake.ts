/**
 * Test-only in-memory doubles for the SDK's QC services
 * (`QualityControlHistoryService` / `QualityControlSessionService` /
 * `QualityControlOperationService`). They return `ApiResponse` like the real
 * services and enforce the invariants the orchestration relies on (one
 * in-progress session per history, append-only operations, overlap-based
 * session dependencies). Not shipped: the real QC client lives in
 * `@hydroserver/client`.
 */

import type {
  ApiResponse,
  QualityControlHistoryService,
  QualityControlSessionService,
  QualityControlOperationService,
  QualityControlHistoryContract,
  QualityControlSessionContract,
  QualityControlOperationContract,
} from '@hydroserver/client'

type QcHistoryDetail = QualityControlHistoryContract.DetailResponse
type QcSessionDetail = QualityControlSessionContract.DetailResponse
type QcSessionSummary = QualityControlSessionContract.SummaryResponse
type QcOperation = QualityControlOperationContract.SummaryResponse
type QcOperationPostBody = QualityControlOperationContract.PostBody[number]
type QcContact = { name: string; email: string }

const ok = <T>(data: T): ApiResponse<T> =>
  ({ data, status: 200, message: '', ok: true }) as ApiResponse<T>
const fail = (message: string, status = 400): ApiResponse<any> =>
  ({ data: null, status, message, ok: false }) as unknown as ApiResponse<any>

const TEST_USER: QcContact = { name: 'Test User', email: 'test@example.org' }

let seq = 0
const nextId = (prefix: string) => `${prefix}-${(seq += 1)}`

const summary = (s: QcSessionDetail): QcSessionSummary => {
  const { operations: _o, dependencyIds: _d, ...rest } = s
  return rest as QcSessionSummary
}

export interface QcFake {
  histories: QualityControlHistoryService
  sessions: QualityControlSessionService
  operations: QualityControlOperationService
}

export function makeQcFake(createdBy: QcContact = TEST_USER): QcFake {
  const histories: QcHistoryDetail[] = []
  const sessions: QcSessionDetail[] = []

  const forHistory = (historyId: string) =>
    sessions.filter((s) => s.historyId === historyId)
  const find = (sessionId: string) => sessions.find((s) => s.id === sessionId)

  /** Transitive committed ancestors of a session (overlap-based dependencies). */
  const ancestorsOf = (sessionId: string): Set<string> => {
    const result = new Set<string>()
    const visit = (id: string) => {
      const s = find(id)
      if (!s) return
      for (const dep of s.dependencyIds) {
        if (!result.has(dep)) {
          result.add(dep)
          visit(dep)
        }
      }
    }
    visit(sessionId)
    return result
  }

  const historiesService = {
    async create(body: QualityControlHistoryContract.PostBody) {
      const history = {
        id: nextId('h'),
        createdAt: '2025-01-01T00:00:00Z',
        managedDatastream: {
          id: body.managedDatastreamId,
          name: `Datastream ${body.managedDatastreamId}`,
        },
        sourceDatastream: {
          id: body.sourceDatastreamId,
          name: `Datastream ${body.sourceDatastreamId}`,
        },
        phenomenonTimeStart: null,
        phenomenonTimeEnd: null,
        sourceChecksum: null,
        managedChecksum: null,
      } as unknown as QcHistoryDetail
      histories.push(history)
      return ok(history)
    },

    async list(
      query?: Partial<QualityControlHistoryContract.QueryParameters>
    ) {
      let list = histories
      const managedIds = query?.managed_datastream_id
      if (managedIds && managedIds.length) {
        list = list.filter((h) => managedIds.includes(h.managedDatastream.id))
      }
      return ok([...list] as QcHistoryDetail[])
    },

    async get(historyId: string) {
      const h = histories.find((x) => x.id === historyId)
      return h ? ok(h) : fail('history not found', 404)
    },

    async delete(historyId: string) {
      const i = histories.findIndex((x) => x.id === historyId)
      if (i >= 0) histories.splice(i, 1)
      return ok(null)
    },
  }

  const sessionsService = {
    async create(historyId: string, body: QualityControlSessionContract.PostBody) {
      if (forHistory(historyId).some((s) => s.status === 'in_progress')) {
        return fail('history already has an in-progress session')
      }
      const id = nextId('s')
      const start = body.phenomenonTimeStart
      const end = body.phenomenonTimeEnd
      // Distinct, increasing creation stamps so ordering by `createdAt` is
      // meaningful even when sessions share a phenomenon-time window.
      const createdAt = new Date(Date.UTC(2025, 0, 1, 0, 0, seq)).toISOString()
      const dependencyIds = forHistory(historyId)
        .filter(
          (s) =>
            s.status === 'committed' &&
            s.phenomenonTimeStart < end &&
            s.phenomenonTimeEnd > start
        )
        .map((s) => s.id)
      const session = {
        id,
        historyId,
        createdBy,
        createdAt,
        phenomenonTimeStart: start,
        phenomenonTimeEnd: end,
        status: 'in_progress',
        committedAt: null,
        description: body.description ?? null,
        sourceChecksum: `chk-${id}`,
        managedChecksum: null,
        dependencyIds,
        operations: [],
      } as unknown as QcSessionDetail
      sessions.push(session)
      return ok({ ...session, operations: [] } as QcSessionDetail)
    },

    async get(historyId: string, sessionId: string) {
      const s = find(sessionId)
      if (!s || s.historyId !== historyId) return fail('session not found', 404)
      return ok({ ...s, operations: [...s.operations] } as QcSessionDetail)
    },

    async list(
      historyId: string,
      query?: Partial<QualityControlSessionContract.QueryParameters>
    ) {
      let list = forHistory(historyId)
      if (query?.ancestor_of) {
        const ids = ancestorsOf(query.ancestor_of)
        list = list.filter((s) => ids.has(s.id))
      }
      if (query?.status) list = list.filter((s) => s.status === query.status)
      // Mirrors the API: `expand_related` returns the detail shape, which
      // embeds each session's operations.
      if (query?.expand_related) {
        return ok(list.map((s) => ({ ...s, operations: [...s.operations] })))
      }
      return ok(list.map(summary))
    },

    async update(
      _historyId: string,
      sessionId: string,
      body: { description?: string | null }
    ) {
      const s = find(sessionId)
      if (!s) return fail('session not found', 404)
      if (body.description !== undefined) s.description = body.description
      return ok({ ...s, operations: [...s.operations] } as QcSessionDetail)
    },

    async delete(_historyId: string, sessionId: string) {
      const i = sessions.findIndex((x) => x.id === sessionId)
      if (i >= 0) sessions.splice(i, 1)
      return ok(null)
    },

    async commit(_historyId: string, sessionId: string) {
      const s = find(sessionId)
      if (!s) return fail('session not found', 404)
      s.status = 'committed'
      // Increasing stamps so commit order is distinguishable, which is what
      // orders a session's ancestor chain on reconstruction.
      s.committedAt = new Date(Date.UTC(2025, 5, 1, 0, 0, (seq += 1))).toISOString()
      s.managedChecksum = `mchk-${sessionId}`
      return ok({ ...s, operations: [...s.operations] } as QcSessionDetail)
    },
  }

  const operationsService = {
    async list(_historyId: string, sessionId: string) {
      const s = find(sessionId)
      return ok(s ? [...s.operations] : [])
    },

    async create(
      _historyId: string,
      sessionId: string,
      body: QcOperationPostBody[]
    ) {
      const s = find(sessionId)
      if (!s) return fail('session not found', 404)
      const created = body.map(
        (b, i): QcOperation =>
          ({
            id: nextId('op'),
            order: b.order ?? s.operations.length + i,
            operationType: b.operationType,
            createdAt: '2025-01-01T00:00:00Z',
            createdBy,
            comment: b.comment ?? null,
            arguments: b.arguments ?? null,
          }) as unknown as QcOperation
      )
      s.operations.push(...created)
      return ok(created)
    },

    async update(
      _historyId: string,
      sessionId: string,
      operationId: string,
      body: { comment?: string | null; order?: number }
    ) {
      const s = find(sessionId)
      if (s?.status === 'committed') {
        return fail('Operations can only be updated in an in-progress session.')
      }
      const op = s?.operations.find((o) => o.id === operationId)
      if (!op) return fail('operation not found', 404)
      if (body.comment !== undefined) (op as any).comment = body.comment
      if (body.order !== undefined) (op as any).order = body.order
      return ok(op)
    },

    async delete(_historyId: string, sessionId: string, operationId: string) {
      const s = find(sessionId)
      if (s) s.operations = s.operations.filter((o) => o.id !== operationId)
      return ok(null)
    },
  }

  return {
    histories: historiesService as unknown as QualityControlHistoryService,
    sessions: sessionsService as unknown as QualityControlSessionService,
    operations: operationsService as unknown as QualityControlOperationService,
  }
}
