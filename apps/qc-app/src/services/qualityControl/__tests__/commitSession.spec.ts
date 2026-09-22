import { describe, it, expect, vi } from 'vitest'
import { makeQcFake } from './qcServiceFake'
import { commitQcSession } from '../commitSession'
import { unwrap } from '../unwrap'

const WIN = {
  phenomenonTimeStart: '2025-01-01T00:00:00Z',
  phenomenonTimeEnd: '2025-02-01T00:00:00Z',
}

const setup = async () => {
  const qc = makeQcFake()
  const h = unwrap(
    await qc.histories.create({
      managedDatastreamId: 'm-1',
      sourceDatastreamId: 's-1',
    })
  )
  const session = unwrap(await qc.sessions.create(h.id, WIN))
  return { qc, historyId: h.id, session }
}

describe('commitQcSession', () => {
  it('checks checksum C, pushes observations, then commits', async () => {
    const { qc, historyId, session } = await setup()
    const order: string[] = []
    const pushObservations = vi.fn(async () => {
      order.push('push')
    })

    const result = await commitQcSession({
      qcSessions: qc.sessions,
      historyId,
      sessionId: session.id,
      currentSourceChecksum: session.sourceChecksum,
      pushObservations,
    })
    order.push('commit')

    expect(pushObservations).toHaveBeenCalledTimes(1)
    expect(order).toEqual(['push', 'commit']) // push before commit
    expect(result.status).toBe('committed')
    expect(result.committedAt).toBeTruthy()
    expect(unwrap(await qc.sessions.get(historyId, session.id)).status).toBe(
      'committed'
    )
  })

  it('blocks the commit on a checksum-C mismatch (no push, stays in progress)', async () => {
    const { qc, historyId, session } = await setup()
    const pushObservations = vi.fn()

    await expect(
      commitQcSession({
        qcSessions: qc.sessions,
        historyId,
        sessionId: session.id,
        currentSourceChecksum: 'changed-checksum',
        pushObservations,
      })
    ).rejects.toThrow(/checksum C/)

    expect(pushObservations).not.toHaveBeenCalled()
    expect(unwrap(await qc.sessions.get(historyId, session.id)).status).toBe(
      'in_progress'
    )
  })

  it('rejects committing an already-committed session', async () => {
    const { qc, historyId, session } = await setup()
    await qc.sessions.commit(historyId, session.id)
    const pushObservations = vi.fn()

    await expect(
      commitQcSession({
        qcSessions: qc.sessions,
        historyId,
        sessionId: session.id,
        currentSourceChecksum: session.sourceChecksum,
        pushObservations,
      })
    ).rejects.toThrow(/in-progress/)
    expect(pushObservations).not.toHaveBeenCalled()
  })
})
