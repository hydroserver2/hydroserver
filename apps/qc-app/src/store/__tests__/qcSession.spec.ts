import { describe, it, expect, beforeEach } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { useHydroServer } from '@/store/hydroserver'
import { makeQcFake } from '@/services/qualityControl/__tests__/qcServiceFake'
import { useQcSessionStore } from '@/store/qcSession'
import { unwrap } from '@/services/qualityControl/unwrap'

const win = (start: string, end: string) => ({
  phenomenonTimeStart: start,
  phenomenonTimeEnd: end,
})

let qc: ReturnType<typeof makeQcFake>

beforeEach(() => {
  createTestPinia()
  qc = makeQcFake()
  useHydroServer().hs = {
    qualityControlHistories: qc.histories,
    qualityControlSessions: qc.sessions,
    qualityControlOperations: qc.operations,
  } as any
})

/** Seed a history with one committed session and one in-progress session. */
async function seed() {
  const h = unwrap(
    await qc.histories.create({
      managedDatastreamId: 'm-1',
      sourceDatastreamId: 's-1',
    })
  )
  const committed = unwrap(
    await qc.sessions.create(h.id, win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z'))
  )
  await qc.sessions.commit(h.id, committed.id)
  const inProgress = unwrap(
    await qc.sessions.create(h.id, win('2025-02-01T00:00:00Z', '2025-03-01T00:00:00Z'))
  )
  return { historyId: h.id, committedId: committed.id, inProgressId: inProgress.id }
}

describe('useQcSessionStore', () => {
  it('loads sessions and defaults the view to the in-progress session', async () => {
    const { historyId, inProgressId } = await seed()
    const store = useQcSessionStore()
    await store.loadSessions(historyId)

    expect(store.historyId).toBe(historyId)
    expect(store.sessions).toHaveLength(2)
    expect(store.currentSessionId).toBe(inProgressId)
    expect(store.viewedSessionId).toBe(inProgressId)
    expect(store.isReadOnly).toBe(false)
    expect(store.committedSessions).toHaveLength(1)
    expect(store.inProgressSession?.id).toBe(inProgressId)
  })

  it('viewing a committed session is read-only; returnToCurrent restores editing', async () => {
    const { historyId, committedId, inProgressId } = await seed()
    const store = useQcSessionStore()
    await store.loadSessions(historyId)

    store.viewSession(committedId)
    expect(store.viewedSessionId).toBe(committedId)
    expect(store.viewedSession?.status).toBe('committed')
    expect(store.isReadOnly).toBe(true)

    store.returnToCurrent()
    expect(store.viewedSessionId).toBe(inProgressId)
    expect(store.isReadOnly).toBe(false)
  })

  it('ignores viewSession for an unknown session id', async () => {
    const { historyId, inProgressId } = await seed()
    const store = useQcSessionStore()
    await store.loadSessions(historyId)
    store.viewSession('does-not-exist')
    expect(store.viewedSessionId).toBe(inProgressId)
  })

  it('with no in-progress session, defaults to the latest committed and is read-only', async () => {
    const h = unwrap(
      await qc.histories.create({
        managedDatastreamId: 'm-1',
        sourceDatastreamId: 's-1',
      })
    )
    const a = unwrap(
      await qc.sessions.create(h.id, win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z'))
    )
    await qc.sessions.commit(h.id, a.id)
    const b = unwrap(
      await qc.sessions.create(h.id, win('2025-02-01T00:00:00Z', '2025-03-01T00:00:00Z'))
    )
    await qc.sessions.commit(h.id, b.id)

    const store = useQcSessionStore()
    await store.loadSessions(h.id)

    expect(store.currentSessionId).toBeNull()
    expect(store.viewedSessionId).toBe(b.id)
    expect(store.isReadOnly).toBe(true)
  })
})
