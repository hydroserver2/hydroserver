import { describe, it, expect, vi } from 'vitest'
import type { Datastream } from '@hydroserver/client'
import type { ObservationRecord } from '@uwrl/qc-utils'
import { makeQcFake } from './qcServiceFake'
import {
  getInProgressSession,
  startOrResumeSession,
  loadSourceWindow,
} from '../session'
import { unwrap } from '../unwrap'

const WIN = {
  phenomenonTimeStart: '2025-01-01T00:00:00Z',
  phenomenonTimeEnd: '2025-02-01T00:00:00Z',
}

const historyWith = async (qc: ReturnType<typeof makeQcFake>) => {
  const h = unwrap(
    await qc.histories.create({
      managedDatastreamId: 'm-1',
      sourceDatastreamId: 's-1',
    })
  )
  return h.id
}

describe('getInProgressSession', () => {
  it('returns null when no session is in progress', async () => {
    const qc = makeQcFake()
    expect(await getInProgressSession(qc.sessions, await historyWith(qc))).toBeNull()
  })

  it('returns the in-progress session when one exists', async () => {
    const qc = makeQcFake()
    const historyId = await historyWith(qc)
    const s = unwrap(await qc.sessions.create(historyId, WIN))
    const found = await getInProgressSession(qc.sessions, historyId)
    expect(found?.id).toBe(s.id)
    expect(found?.status).toBe('in_progress')
  })
})

describe('startOrResumeSession', () => {
  it('starts a new session when none is in progress', async () => {
    const qc = makeQcFake()
    const historyId = await historyWith(qc)
    const session = await startOrResumeSession(qc.sessions, historyId, {
      ...WIN,
      description: 'Jan QC',
    })
    expect(session.status).toBe('in_progress')
    expect(session.description).toBe('Jan QC')
    expect(unwrap(await qc.sessions.list(historyId))).toHaveLength(1)
  })

  it('resumes the existing session instead of creating another (spec ignored)', async () => {
    const qc = makeQcFake()
    const historyId = await historyWith(qc)
    const first = unwrap(await qc.sessions.create(historyId, WIN))
    const resumed = await startOrResumeSession(qc.sessions, historyId, {
      phenomenonTimeStart: '2030-01-01T00:00:00Z',
      phenomenonTimeEnd: '2030-02-01T00:00:00Z',
    })
    expect(resumed.id).toBe(first.id)
    expect(resumed.phenomenonTimeStart).toBe(WIN.phenomenonTimeStart)
    expect(unwrap(await qc.sessions.list(historyId))).toHaveLength(1)
  })
})

describe('loadSourceWindow', () => {
  it('fetches the session window from the source datastream', async () => {
    const record = {} as ObservationRecord
    const fetchInRange = vi.fn().mockResolvedValue(record)
    const source = { id: 's-1' } as unknown as Datastream

    const result = await loadSourceWindow(fetchInRange, source, WIN)

    expect(result).toBe(record)
    expect(fetchInRange).toHaveBeenCalledTimes(1)
    const [ds, begin, end] = fetchInRange.mock.calls[0]
    expect(ds).toBe(source)
    expect((begin as Date).toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect((end as Date).toISOString()).toBe('2025-02-01T00:00:00.000Z')
  })
})
