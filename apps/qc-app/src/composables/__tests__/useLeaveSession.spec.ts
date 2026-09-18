import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'

const {
  qcDatastream,
  resumeDatastreamId,
  historyId,
  sessions,
  inProgressSession,
  isReadOnly,
  hasSessionOperations,
  hasUnsavedChanges,
  unsavedEditCount,
  saveDraft,
  discardUnsavedEdits,
  deleteSessionChain,
  applySessions,
  redraw,
  invalidate,
  success,
  error,
} = vi.hoisted(() => {
  const { ref: r } = require('vue') as typeof import('vue')
  return {
    qcDatastream: r<{ id: string } | null>(null),
    resumeDatastreamId: r<string | null>(null),
    historyId: r<string | null>('h-1'),
    sessions: r<Array<{ id: string; dependencyIds?: string[] }>>([]),
    inProgressSession: r<{ id: string } | null>(null),
    isReadOnly: r(false),
    hasSessionOperations: r(false),
    hasUnsavedChanges: r(false),
    unsavedEditCount: r(0),
    saveDraft: vi.fn(),
    discardUnsavedEdits: vi.fn(),
    deleteSessionChain: vi.fn(),
    applySessions: vi.fn(),
    redraw: vi.fn(),
    invalidate: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
  }
})

vi.mock('@/store/dataVisualization', async () => {
  const { defineStore } = await import('pinia')
  return {
    useDataVisStore: defineStore('dataVisualization', () => ({ qcDatastream })),
  }
})

vi.mock('@/store/qcSession', async () => {
  const { defineStore } = await import('pinia')
  return {
    useQcSessionStore: defineStore('qcSession', () => ({
      resumeDatastreamId,
      historyId,
      sessions,
      inProgressSession,
      isReadOnly,
      hasSessionOperations,
      applySessions,
    })),
  }
})

vi.mock('@/store/plotly', () => ({ usePlotlyStore: () => ({ redraw }) }))

vi.mock('@/store/workingCopies', () => ({
  useWorkingCopiesStore: () => ({ invalidate }),
}))

vi.mock('@/composables/useEditSession', () => ({
  useEditSession: () => ({
    hasUnsavedChanges,
    unsavedEditCount,
    saveDraft,
    discardUnsavedEdits,
  }),
}))

vi.mock('@/composables/useManagedDatastreams', () => ({
  useManagedDatastreams: () => ({ deleteSessionChain }),
}))

vi.mock('@uwrl/qc-utils', () => ({ Snackbar: { success, error } }))

import { useLeaveSession } from '../useLeaveSession'

/** Let every already-settled promise deliver before asserting. */
const tick = () => new Promise((resolve) => setTimeout(resolve, 0))

/** Nothing saved, nothing unsaved: an untouched in-progress session. */
function emptySession() {
  qcDatastream.value = { id: 'mgd-1' }
  inProgressSession.value = { id: 'qcs-1' }
  sessions.value = [{ id: 'qcs-1' }]
  hasSessionOperations.value = false
  hasUnsavedChanges.value = false
}

beforeEach(() => {
  createTestPinia()
  vi.clearAllMocks()
  qcDatastream.value = { id: 'mgd-1' }
  resumeDatastreamId.value = 'mgd-1'
  historyId.value = 'h-1'
  sessions.value = []
  inProgressSession.value = null
  isReadOnly.value = false
  hasSessionOperations.value = false
  hasUnsavedChanges.value = false
  unsavedEditCount.value = 0
  saveDraft.mockResolvedValue(undefined)
  discardUnsavedEdits.mockResolvedValue(undefined)
  deleteSessionChain.mockResolvedValue(['qcs-1'])
})

describe('leaveCase', () => {
  it('is none with nothing being edited', () => {
    qcDatastream.value = null
    expect(useLeaveSession().leaveCase()).toBe('none')
  })

  it('is none while viewing committed history', () => {
    emptySession()
    isReadOnly.value = true
    expect(useLeaveSession().leaveCase()).toBe('none')
  })

  it('is none when the editor is open with no session', () => {
    expect(useLeaveSession().leaveCase()).toBe('none')
  })

  it('is unsaved when edits have not reached the session', () => {
    emptySession()
    hasUnsavedChanges.value = true
    expect(useLeaveSession().leaveCase()).toBe('unsaved')
  })

  it('is empty when the session holds nothing', () => {
    emptySession()
    expect(useLeaveSession().leaveCase()).toBe('empty')
  })

  it('is saved when the session holds operations', () => {
    emptySession()
    hasSessionOperations.value = true
    expect(useLeaveSession().leaveCase()).toBe('saved')
  })
})

describe('requestLeave', () => {
  it('leaves without asking when there is nothing to decide', async () => {
    const { requestLeave, leavePrompt } = useLeaveSession()
    expect(await requestLeave()).toBe(true)
    expect(leavePrompt.value).toBeNull()
  })

  it('asks about unsaved edits and reports whether saving is possible', async () => {
    emptySession()
    hasUnsavedChanges.value = true
    unsavedEditCount.value = 3
    const { requestLeave, leavePrompt, cancelLeave } = useLeaveSession()
    const pending = requestLeave()

    expect(leavePrompt.value).toEqual({
      kind: 'unsaved',
      unsavedCount: 3,
      canSave: true,
    })
    cancelLeave()
    expect(await pending).toBe(false)
    expect(leavePrompt.value).toBeNull()
  })

  it('cannot save with no session open', async () => {
    qcDatastream.value = { id: 'mgd-1' }
    hasUnsavedChanges.value = true
    const { requestLeave, leavePrompt, saveAndLeave, cancelLeave } =
      useLeaveSession()
    const pending = requestLeave()

    expect(leavePrompt.value?.canSave).toBe(false)
    await saveAndLeave()
    expect(saveDraft).not.toHaveBeenCalled()
    expect(leavePrompt.value).not.toBeNull()

    cancelLeave()
    await pending
  })

  it('saves the draft and leaves', async () => {
    emptySession()
    hasUnsavedChanges.value = true
    const { requestLeave, saveAndLeave, leavePrompt } = useLeaveSession()
    const pending = requestLeave()

    await saveAndLeave()

    expect(saveDraft).toHaveBeenCalled()
    expect(await pending).toBe(true)
    expect(leavePrompt.value).toBeNull()
  })

  it('keeps the user in the session when the save fails', async () => {
    emptySession()
    hasUnsavedChanges.value = true
    saveDraft.mockRejectedValueOnce(new Error('offline'))
    const { requestLeave, saveAndLeave, leavePrompt, cancelLeave } =
      useLeaveSession()
    const pending = requestLeave()

    await saveAndLeave()

    expect(error).toHaveBeenCalledWith('offline')
    expect(leavePrompt.value?.kind).toBe('unsaved')

    cancelLeave()
    expect(await pending).toBe(false)
  })

  it('discards the edits and leaves when the session keeps operations', async () => {
    emptySession()
    hasUnsavedChanges.value = true
    hasSessionOperations.value = true
    const { requestLeave, discardEditsAndLeave } = useLeaveSession()
    const pending = requestLeave()

    await discardEditsAndLeave()

    expect(discardUnsavedEdits).toHaveBeenCalled()
    expect(redraw).toHaveBeenCalled()
    expect(await pending).toBe(true)
  })

  it('asks about the empty session when discarding leaves nothing', async () => {
    emptySession()
    hasUnsavedChanges.value = true
    const { requestLeave, discardEditsAndLeave, leavePrompt, keepSession } =
      useLeaveSession()
    const pending = requestLeave()

    await discardEditsAndLeave()

    expect(leavePrompt.value?.kind).toBe('empty')
    keepSession()
    expect(await pending).toBe(true)
  })

  it('keeps the user in the session when discarding the edits fails', async () => {
    emptySession()
    hasUnsavedChanges.value = true
    discardUnsavedEdits.mockRejectedValueOnce(new Error('no record'))
    const { requestLeave, discardEditsAndLeave, leavePrompt, cancelLeave } =
      useLeaveSession()
    const pending = requestLeave()

    await discardEditsAndLeave()

    expect(error).toHaveBeenCalledWith('no record')
    expect(leavePrompt.value?.kind).toBe('unsaved')
    cancelLeave()
    expect(await pending).toBe(false)
  })

  it('keeps an empty session on the server when asked to', async () => {
    emptySession()
    const { requestLeave, keepSession } = useLeaveSession()
    const pending = requestLeave()

    keepSession()

    expect(await pending).toBe(true)
    expect(deleteSessionChain).not.toHaveBeenCalled()
  })

  it('deletes only the empty session itself', async () => {
    emptySession()
    const { requestLeave, discardSessionAndLeave } = useLeaveSession()
    const pending = requestLeave()

    await discardSessionAndLeave()

    expect(deleteSessionChain).toHaveBeenCalledWith('h-1', ['qcs-1'])
    expect(invalidate).toHaveBeenCalledWith('mgd-1')
    // The store no longer lists a session the server does not have.
    expect(applySessions).toHaveBeenCalledWith('h-1', [])
    expect(await pending).toBe(true)
  })

  it('refuses to discard a session another one was built on', async () => {
    emptySession()
    sessions.value = [
      { id: 'qcs-1' },
      { id: 'qcs-2', dependencyIds: ['qcs-1'] },
    ]
    const { requestLeave, discardSessionAndLeave, leavePrompt, cancelLeave } =
      useLeaveSession()
    const pending = requestLeave()

    await discardSessionAndLeave()

    expect(deleteSessionChain).not.toHaveBeenCalled()
    expect(error).toHaveBeenCalled()
    expect(leavePrompt.value?.kind).toBe('empty')
    cancelLeave()
    expect(await pending).toBe(false)
  })

  it('keeps the user in the session when the delete fails', async () => {
    emptySession()
    deleteSessionChain.mockRejectedValueOnce(new Error('server said no'))
    const { requestLeave, discardSessionAndLeave, leavePrompt, cancelLeave } =
      useLeaveSession()
    const pending = requestLeave()

    await discardSessionAndLeave()

    expect(error).toHaveBeenCalledWith('server said no')
    expect(leavePrompt.value?.kind).toBe('empty')
    cancelLeave()
    expect(await pending).toBe(false)
  })

  it('asks before leaving a session whose edits are all saved', async () => {
    emptySession()
    hasSessionOperations.value = true
    const { requestLeave, leavePrompt, closeSession } = useLeaveSession()
    const pending = requestLeave()

    expect(leavePrompt.value?.kind).toBe('saved')
    closeSession()

    expect(await pending).toBe(true)
    expect(deleteSessionChain).not.toHaveBeenCalled()
  })

  it('a second request supersedes the first, which stays put', async () => {
    emptySession()
    const { requestLeave, cancelLeave } = useLeaveSession()
    const first = requestLeave()
    const second = requestLeave()

    expect(await first).toBe(false)
    cancelLeave()
    expect(await second).toBe(false)
  })

  it('refuses a second request while the first answer is being carried out', async () => {
    emptySession()
    hasUnsavedChanges.value = true
    let finishSave!: () => void
    saveDraft.mockImplementationOnce(
      () => new Promise<void>((resolve) => (finishSave = resolve))
    )
    const { requestLeave, saveAndLeave } = useLeaveSession()
    const first = requestLeave()
    void saveAndLeave()
    await tick()

    // The save is still running, so the second exit is refused outright
    // rather than inheriting the answer the user gave the first one.
    const second = requestLeave()
    expect(await Promise.race([second, tick().then(() => 'unanswered')])).toBe(
      false
    )

    finishSave()
    expect(await first).toBe(true)
  })
})

describe('forgetSession', () => {
  it('drops the pointer that reopens the editor', () => {
    useLeaveSession().forgetSession()
    expect(resumeDatastreamId.value).toBeNull()
  })
})
