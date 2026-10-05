import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'

// vi.mock factories are hoisted above module-level consts, so anything they
// close over has to be created inside vi.hoisted.
const {
  qcDatastream,
  setEditTarget,
  clearEditTarget,
  beginEditing,
  startSession,
  currentView,
  selectedDrawer,
  isDrawerOpen,
  resumeDatastreamId,
  openingDatastreamId,
  success,
  error,
  requestLeave,
  forgetSession,
  ResumeSupersededError,
} = vi.hoisted(() => {
  const { ref: r } = require('vue') as typeof import('vue')
  class ResumeSupersededError extends Error {
    constructor() {
      super('superseded')
      this.name = 'ResumeSupersededError'
    }
  }
  const resumeDatastreamId = r<string | null>(null)
  return {
    qcDatastream: r<{ id: string } | null>(null),
    setEditTarget: vi.fn(),
    clearEditTarget: vi.fn(),
    beginEditing: vi.fn(),
    startSession: vi.fn(),
    currentView: r('Select'),
    selectedDrawer: r('Select'),
    isDrawerOpen: r(false),
    resumeDatastreamId,
    openingDatastreamId: r<string | null>(null),
    success: vi.fn(),
    error: vi.fn(),
    requestLeave: vi.fn(),
    forgetSession: vi.fn(() => {
      resumeDatastreamId.value = null
    }),
    ResumeSupersededError,
  }
})

// Real Pinia stores, so `storeToRefs` behaves as it does in production.
vi.mock('@/store/dataVisualization', async () => {
  const { defineStore } = await import('pinia')
  return {
    useDataVisStore: defineStore('dataVisualization', () => ({
      qcDatastream,
      setEditTarget,
      clearEditTarget,
    })),
  }
})

vi.mock('@/store/userInterface', async () => {
  const { defineStore } = await import('pinia')
  return {
    DrawerType: { Edit: 'Edit', Select: 'Select', None: '' },
    useUIStore: defineStore('userInterface', () => ({
      currentView,
      selectedDrawer,
      isDrawerOpen,
      showView: (view: string) => {
        currentView.value = view
        selectedDrawer.value = view
        isDrawerOpen.value = true
      },
    })),
  }
})

vi.mock('@/composables/useLeaveSession', () => ({
  useLeaveSession: () => ({ requestLeave, forgetSession }),
}))

vi.mock('@/store/qcSession', async () => {
  const { defineStore } = await import('pinia')
  return {
    useQcSessionStore: defineStore('qcSession', () => ({
      resumeDatastreamId,
      openingDatastreamId,
    })),
  }
})

vi.mock('@/composables/useEditSession', () => ({
  ResumeSupersededError,
  useEditSession: () => ({
    beginEditing,
    startSession,
  }),
}))

vi.mock('@uwrl/qc-utils', () => ({ Snackbar: { success, error } }))

import { useEditEntry } from '../useEditEntry'
import { DrawerType } from '@/store/userInterface'

const window = {
  begin: new Date('2025-01-01T00:00:00Z'),
  end: new Date('2025-02-01T00:00:00Z'),
}

beforeEach(() => {
  createTestPinia()
  vi.clearAllMocks()
  currentView.value = 'Select'
  selectedDrawer.value = 'Select'
  isDrawerOpen.value = false
  resumeDatastreamId.value = null
  openingDatastreamId.value = null
  qcDatastream.value = null
  setEditTarget.mockImplementation(async (id: string) => {
    qcDatastream.value = { id }
  })
  clearEditTarget.mockImplementation(async () => {
    qcDatastream.value = null
  })
  beginEditing.mockResolvedValue('resumed')
  startSession.mockResolvedValue(undefined)
  requestLeave.mockResolvedValue(true)
})

describe('useEditEntry', () => {
  it('resumes into the editor when a session is in progress', async () => {
    const result = await useEditEntry().enterEdit('mgd')
    expect(setEditTarget).toHaveBeenCalledWith('mgd')
    expect(result).toBe('editing')
    expect(currentView.value).toBe('Edit')
    expect(resumeDatastreamId.value).toBe('mgd')
  })

  it('asks for a window when there is no session and none was given', async () => {
    beginEditing.mockResolvedValue('needs-session')
    expect(await useEditEntry().enterEdit('mgd')).toBe('needs-window')
    expect(startSession).not.toHaveBeenCalled()
  })

  it('starts a session over the given window', async () => {
    beginEditing.mockResolvedValue('needs-session')
    expect(await useEditEntry().enterEdit('mgd', window)).toBe('editing')
    expect(startSession).toHaveBeenCalledWith({
      phenomenonTimeStart: '2025-01-01T00:00:00.000Z',
      phenomenonTimeEnd: '2025-02-01T00:00:00.000Z',
    })
  })

  it('keeps the editor open when starting the session fails', async () => {
    beginEditing.mockResolvedValue('needs-session')
    startSession.mockRejectedValueOnce(new Error('bad window'))
    expect(await useEditEntry().enterEdit('mgd', window)).toBe('needs-window')
    expect(error).toHaveBeenCalledWith('bad window')
    expect(currentView.value).toBe('Edit')
    expect(clearEditTarget).not.toHaveBeenCalled()
  })

  it('leaves the editor when the new session was superseded', async () => {
    beginEditing.mockResolvedValue('needs-session')
    startSession.mockRejectedValueOnce(new ResumeSupersededError())
    expect(await useEditEntry().enterEdit('mgd', window)).toBe('superseded')
    expect(currentView.value).toBe('Select')
    expect(clearEditTarget).toHaveBeenCalled()
  })

  it('leaves the editor when the resume was superseded', async () => {
    beginEditing.mockRejectedValueOnce(new ResumeSupersededError())
    expect(await useEditEntry().enterEdit('mgd')).toBe('superseded')
    expect(error).toHaveBeenCalledWith('superseded')
    expect(currentView.value).toBe('Select')
    expect(resumeDatastreamId.value).toBeNull()
  })

  it('says nothing when the editor was closed while the session opened', async () => {
    beginEditing.mockImplementationOnce(async () => {
      qcDatastream.value = null
      throw new ResumeSupersededError()
    })
    expect(await useEditEntry().enterEdit('mgd')).toBe('superseded')
    expect(error).not.toHaveBeenCalled()
    expect(currentView.value).toBe('Select')
  })

  it('says nothing when the editor was closed while a new session started', async () => {
    beginEditing.mockResolvedValue('needs-session')
    startSession.mockImplementationOnce(async () => {
      qcDatastream.value = null
      throw new ResumeSupersededError()
    })
    expect(await useEditEntry().enterEdit('mgd', window)).toBe('superseded')
    expect(error).not.toHaveBeenCalled()
    expect(currentView.value).toBe('Select')
  })

  it('leaves the editor and rethrows any other resume failure', async () => {
    beginEditing.mockRejectedValueOnce(new Error('offline'))
    await expect(useEditEntry().enterEdit('mgd')).rejects.toThrow('offline')
    expect(clearEditTarget).toHaveBeenCalled()
    expect(currentView.value).toBe('Select')
  })

  it('leaves the editor and rethrows when setting the target fails', async () => {
    setEditTarget.mockImplementationOnce(async (id: string) => {
      qcDatastream.value = { id }
      throw new Error('rebuild failed')
    })
    resumeDatastreamId.value = 'mgd'
    await expect(useEditEntry().enterEdit('mgd')).rejects.toThrow(
      'rebuild failed'
    )
    expect(clearEditTarget).toHaveBeenCalled()
    expect(resumeDatastreamId.value).toBeNull()
    expect(currentView.value).toBe('Select')
    expect(beginEditing).not.toHaveBeenCalled()
  })

  // A newer entry took over while this one awaited; it owns the view state.
  const takeOverDuringBegin = (outcome: string) =>
    beginEditing.mockImplementation(async () => {
      qcDatastream.value = { id: 'newer' }
      resumeDatastreamId.value = 'newer'
      currentView.value = 'Edit'
      return outcome
    })

  it('stands down when the target changes before a not-managed result', async () => {
    takeOverDuringBegin('not-managed')
    expect(await useEditEntry().enterEdit('mgd')).toBe('superseded')
    expect(clearEditTarget).not.toHaveBeenCalled()
    expect(resumeDatastreamId.value).toBe('newer')
    expect(currentView.value).toBe('Edit')
    expect(error).not.toHaveBeenCalled()
  })

  it('stands down when the target changes before starting a session', async () => {
    takeOverDuringBegin('needs-session')
    expect(await useEditEntry().enterEdit('mgd', window)).toBe('superseded')
    expect(startSession).not.toHaveBeenCalled()
    expect(clearEditTarget).not.toHaveBeenCalled()
    expect(resumeDatastreamId.value).toBe('newer')
  })

  it('does not leave a newer target when its own start is superseded', async () => {
    beginEditing.mockResolvedValue('needs-session')
    startSession.mockImplementationOnce(async () => {
      qcDatastream.value = { id: 'newer' }
      resumeDatastreamId.value = 'newer'
      throw new ResumeSupersededError()
    })
    expect(await useEditEntry().enterEdit('mgd', window)).toBe('superseded')
    expect(clearEditTarget).not.toHaveBeenCalled()
    expect(resumeDatastreamId.value).toBe('newer')
  })

  it('backs out when the datastream has no QC history', async () => {
    beginEditing.mockResolvedValue('not-managed')
    expect(await useEditEntry().enterEdit('mgd')).toBe('not-managed')
    expect(clearEditTarget).toHaveBeenCalled()
    expect(currentView.value).toBe('Select')
  })

  it('startSessionOver reports whether the session started', async () => {
    const { startSessionOver } = useEditEntry()
    expect(await startSessionOver(window)).toBe(true)
    expect(success).toHaveBeenCalledWith('Edit session started.')
    startSession.mockRejectedValueOnce(new Error('nope'))
    expect(await startSessionOver(window)).toBe(false)
  })

  it('lands on Select when the caller asks for it', async () => {
    const result = await useEditEntry().enterEdit(
      'mgd',
      undefined,
      DrawerType.Select
    )
    expect(result).toBe('editing')
    expect(currentView.value).toBe('Select')
    expect(selectedDrawer.value).toBe('Select')
    expect(resumeDatastreamId.value).toBe('mgd')
  })

  it('shows the view while the session opens, flagged as opening', async () => {
    let finish!: (v: string) => void
    beginEditing.mockReturnValueOnce(new Promise((r) => (finish = r)))
    const entering = useEditEntry().enterEdit('mgd')
    await vi.waitFor(() => expect(beginEditing).toHaveBeenCalled())
    expect(currentView.value).toBe('Edit')
    expect(openingDatastreamId.value).toBe('mgd')

    finish('resumed')
    expect(await entering).toBe('editing')
    expect(openingDatastreamId.value).toBeNull()
  })

  it('keeps a view the user switched to while the session opened', async () => {
    let finish!: (v: string) => void
    beginEditing.mockReturnValueOnce(new Promise((r) => (finish = r)))
    const entering = useEditEntry().enterEdit('mgd', undefined, DrawerType.Select)
    await vi.waitFor(() => expect(beginEditing).toHaveBeenCalled())
    currentView.value = 'Edit'

    finish('resumed')
    await entering
    expect(currentView.value).toBe('Edit')
  })

  it('clears the opening flag when the session fails to open', async () => {
    beginEditing.mockRejectedValueOnce(new Error('offline'))
    await expect(useEditEntry().enterEdit('mgd')).rejects.toThrow('offline')
    expect(openingDatastreamId.value).toBeNull()
  })

  it('shows the editor again without re-entering its own target', async () => {
    qcDatastream.value = { id: 'mgd' }
    currentView.value = 'Select'
    expect(await useEditEntry().enterEdit('mgd')).toBe('editing')
    expect(currentView.value).toBe('Edit')
    expect(setEditTarget).not.toHaveBeenCalled()
    expect(beginEditing).not.toHaveBeenCalled()
  })

  it('still starts a session over a window on its own target', async () => {
    qcDatastream.value = { id: 'mgd' }
    beginEditing.mockResolvedValue('needs-session')
    expect(await useEditEntry().enterEdit('mgd', window)).toBe('editing')
    expect(startSession).toHaveBeenCalled()
  })

  it('asks before taking over from another open session', async () => {
    qcDatastream.value = { id: 'other' }
    requestLeave.mockResolvedValueOnce(false)
    expect(await useEditEntry().enterEdit('mgd')).toBe('kept')
    expect(setEditTarget).not.toHaveBeenCalled()
    expect(qcDatastream.value).toEqual({ id: 'other' })
    expect(currentView.value).toBe('Select')
  })

  it('takes over when leaving the open session is allowed', async () => {
    qcDatastream.value = { id: 'other' }
    expect(await useEditEntry().enterEdit('mgd')).toBe('editing')
    expect(requestLeave).toHaveBeenCalled()
    expect(setEditTarget).toHaveBeenCalledWith('mgd')
  })

  it('openEditor shows the editor without touching the target', () => {
    qcDatastream.value = { id: 'mgd' }
    resumeDatastreamId.value = 'mgd'
    useEditEntry().openEditor()
    expect(currentView.value).toBe('Edit')
    expect(selectedDrawer.value).toBe('Edit')
    expect(isDrawerOpen.value).toBe(true)
    expect(clearEditTarget).not.toHaveBeenCalled()
    expect(resumeDatastreamId.value).toBe('mgd')
  })

  it('leaveEdit returns to Select and forgets the resume target', async () => {
    resumeDatastreamId.value = 'mgd'
    currentView.value = 'Edit'
    await useEditEntry().leaveEdit()
    expect(currentView.value).toBe('Select')
    expect(resumeDatastreamId.value).toBeNull()
    expect(clearEditTarget).toHaveBeenCalled()
  })

  it('closeEditor ends the session once the user agrees to leave', async () => {
    qcDatastream.value = { id: 'mgd' }
    resumeDatastreamId.value = 'mgd'
    currentView.value = 'Edit'

    expect(await useEditEntry().closeEditor()).toBe(true)

    expect(requestLeave).toHaveBeenCalled()
    expect(clearEditTarget).toHaveBeenCalled()
    expect(currentView.value).toBe('Select')
    expect(resumeDatastreamId.value).toBeNull()
  })

  it('closeEditor leaves everything in place when the user stays', async () => {
    qcDatastream.value = { id: 'mgd' }
    resumeDatastreamId.value = 'mgd'
    currentView.value = 'Edit'
    requestLeave.mockResolvedValueOnce(false)

    expect(await useEditEntry().closeEditor()).toBe(false)

    expect(clearEditTarget).not.toHaveBeenCalled()
    expect(currentView.value).toBe('Edit')
    expect(resumeDatastreamId.value).toBe('mgd')
  })
})
