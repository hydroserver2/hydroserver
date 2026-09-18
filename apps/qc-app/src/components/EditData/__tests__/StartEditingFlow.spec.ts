import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { VDialog } from 'vuetify/components'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// jsdom has no visualViewport; Vuetify's overlay positioning reads it.
;(globalThis as any).visualViewport ||= {
  addEventListener() {},
  removeEventListener() {},
  offsetLeft: 0,
  offsetTop: 0,
  width: 1024,
  height: 768,
  scale: 1,
}

const {
  loadForSource,
  deleteManaged,
  deleteSession,
  enterEdit,
  startSessionOver,
  leaveEdit,
  closeEditor,
  createManaged,
  addQcHistory,
  removeManagedDatastream,
  invalidate,
  qcDatastream,
  datastreams,
  processingLevels,
  sourceDatastream,
  sessions,
  success,
  error,
} = vi.hoisted(() => {
  const { ref: r } = require('vue') as typeof import('vue')
  return {
    loadForSource: vi.fn(),
    deleteManaged: vi.fn(),
    deleteSession: vi.fn(),
    enterEdit: vi.fn(),
    startSessionOver: vi.fn(),
    leaveEdit: vi.fn(),
    closeEditor: vi.fn(),
    createManaged: vi.fn(),
    addQcHistory: vi.fn(),
    removeManagedDatastream: vi.fn(),
    invalidate: vi.fn(),
    qcDatastream: r<any>(null),
    datastreams: r<any[]>([]),
    processingLevels: r<any[]>([]),
    sourceDatastream: r<any>(null),
    sessions: r<any[]>([]),
    success: vi.fn(),
    error: vi.fn(),
  }
})

vi.mock('@/store/dataVisualization', async () => {
  const { defineStore } = await import('pinia')
  return {
    useDataVisStore: defineStore('dataVisualization', () => ({
      qcDatastream,
      datastreams,
      processingLevels,
      addQcHistory,
      removeManagedDatastream,
    })),
  }
})

vi.mock('@/store/qcSession', async () => {
  const { defineStore } = await import('pinia')
  const { computed } = await import('vue')
  return {
    useQcSessionStore: defineStore('qcSession', () => ({
      sourceDatastream,
      sessions,
      inProgressSession: computed(
        () => sessions.value.find((s) => s.status === 'in_progress') ?? null
      ),
    })),
  }
})

vi.mock('@/store/workingCopies', () => ({
  useWorkingCopiesStore: () => ({ invalidate }),
}))

vi.mock('@/composables/useManagedDatastreams', () => ({
  useManagedDatastreams: () => ({
    loadForSource,
    deleteManaged,
    deleteSession,
  }),
}))

vi.mock('@/composables/useEditEntry', () => ({
  useEditEntry: () => ({ enterEdit, startSessionOver, leaveEdit, closeEditor }),
}))

vi.mock('@/composables/useCreateManagedDatastream', () => ({
  useCreateManagedDatastream: () => ({ create: createManaged }),
}))

vi.mock('@/composables/useProcessingLevels', () => ({
  useProcessingLevels: () => ({ createProcessingLevel: vi.fn() }),
}))

vi.mock('@/composables/useWorkspacePermissions', () => ({
  useWorkspacePermissions: () => ({
    canCreateDatastream: () => true,
    roleName: () => 'Owner',
  }),
}))

vi.mock('@uwrl/qc-utils', () => ({ Snackbar: { success, error } }))

import StartEditingFlow from '@/components/EditData/StartEditingFlow.vue'

const stub = (name: string, testId: string, emits: string[]) =>
  defineComponent({
    name,
    emits,
    setup: () => () => h('div', { 'data-testid': testId }),
  })

const ChooserStub = stub('StartEditingDialog', 'chooser-stub', [
  'edit',
  'delete',
  'deleteSession',
  'create',
  'cancel',
])
const CreateStub = stub('CreateDatastreamForm', 'create-stub', [
  'cancel',
  'confirm',
])
const WindowStub = stub('SessionWindowDialog', 'window-stub', [
  'confirm',
  'cancel',
])

interface FlowApi {
  openFor(source: unknown): Promise<void>
  openNewSession(): void
  resume(managedId: string): Promise<void>
}

const source = {
  id: 'src',
  name: 'Raw Temp',
  phenomenonBeginTime: '2025-01-01T00:00:00Z',
  phenomenonEndTime: '2025-12-31T00:00:00Z',
}
const committed = {
  id: 's-0',
  status: 'committed',
  phenomenonTimeStart: '2025-01-01T00:00:00Z',
  phenomenonTimeEnd: '2025-02-01T00:00:00Z',
}
const inProgress = { ...committed, id: 's-1', status: 'in_progress' }
const optionWith = (list: unknown[]) => ({
  historyId: 'h',
  managed: { id: 'mgd', name: 'Temp (QC)' },
  sessions: list,
})
const window = {
  begin: new Date('2025-02-01T00:00:00Z'),
  end: new Date('2025-03-01T00:00:00Z'),
}

const mountFlow = () => {
  const wrapper = mount(StartEditingFlow, {
    global: {
      plugins: [createTestPinia(), createTestVuetify()],
      stubs: {
        StartEditingDialog: ChooserStub,
        CreateDatastreamForm: CreateStub,
        SessionWindowDialog: WindowStub,
      },
    },
    attachTo: document.body,
  })
  return { wrapper, flow: wrapper.vm as unknown as FlowApi }
}

// v-dialog teleports its content out of the wrapper.
const present = (testId: string) =>
  !!document.querySelector(`[data-testid="${testId}"]`)

// Dialog order: chooser, create form, session window.
const dialogOpen = (wrapper: ReturnType<typeof mountFlow>['wrapper'], i: number) =>
  wrapper.findAllComponents(VDialog)[i].props('modelValue')

enableAutoUnmount(afterEach)
afterEach(() => {
  document.body.innerHTML = ''
})

beforeEach(() => {
  vi.clearAllMocks()
  qcDatastream.value = null
  datastreams.value = []
  processingLevels.value = []
  sourceDatastream.value = null
  sessions.value = []
  enterEdit.mockResolvedValue('editing')
  startSessionOver.mockResolvedValue(true)
  leaveEdit.mockResolvedValue(undefined)
  closeEditor.mockResolvedValue(true)
})

describe('StartEditingFlow', () => {
  it('opens the chooser when the source has managed datastreams', async () => {
    loadForSource.mockResolvedValue([optionWith([committed])])
    const { flow } = mountFlow()
    await flow.openFor(source)
    await flushPromises()
    expect(loadForSource).toHaveBeenCalledWith('src')
    expect(present('chooser-stub')).toBe(true)
    expect(present('create-stub')).toBe(false)
  })

  it('goes straight to the create form when the source has none', async () => {
    loadForSource.mockResolvedValue([])
    const { flow } = mountFlow()
    await flow.openFor(source)
    await flushPromises()
    expect(present('create-stub')).toBe(true)
    expect(present('chooser-stub')).toBe(false)
  })

  it('continues an in-progress session without asking for a window', async () => {
    const option = optionWith([committed, inProgress])
    loadForSource.mockResolvedValue([option])
    const { wrapper, flow } = mountFlow()
    await flow.openFor(source)
    await flushPromises()
    wrapper.findComponent(ChooserStub).vm.$emit('edit', option)
    await flushPromises()
    expect(enterEdit).toHaveBeenCalledTimes(1)
    expect(enterEdit.mock.calls[0]).toEqual(['mgd', undefined, undefined])
    expect(present('window-stub')).toBe(false)
  })

  it('asks for a window before starting a new session', async () => {
    const option = optionWith([committed])
    loadForSource.mockResolvedValue([option])
    const { wrapper, flow } = mountFlow()
    await flow.openFor(source)
    await flushPromises()
    wrapper.findComponent(ChooserStub).vm.$emit('edit', option)
    await flushPromises()
    expect(present('window-stub')).toBe(true)
    expect(enterEdit).not.toHaveBeenCalled()

    wrapper.findComponent(WindowStub).vm.$emit('confirm', window)
    await flushPromises()
    expect(enterEdit).toHaveBeenCalledWith('mgd', window, undefined)
    expect(present('window-stub')).toBe(false)
  })

  it('opens the window step when a resume finds no session', async () => {
    enterEdit.mockResolvedValue('needs-window')
    qcDatastream.value = { id: 'mgd', name: 'Temp (QC)' }
    sourceDatastream.value = source
    const { flow } = mountFlow()
    await flow.resume('mgd')
    await flushPromises()
    expect(enterEdit.mock.calls[0]).toEqual(['mgd', undefined, undefined])
    expect(present('window-stub')).toBe(true)
  })

  it('leaves the editor when the window is cancelled with no sessions at all', async () => {
    enterEdit.mockResolvedValue('needs-window')
    qcDatastream.value = { id: 'mgd', name: 'Temp (QC)' }
    sourceDatastream.value = source
    const { wrapper, flow } = mountFlow()
    await flow.resume('mgd')
    await flushPromises()
    wrapper.findComponent(WindowStub).vm.$emit('cancel')
    await flushPromises()
    expect(leaveEdit).toHaveBeenCalled()
    expect(present('window-stub')).toBe(false)
  })

  it('leaves the editor when the window is closed with Esc or the scrim after an empty resume', async () => {
    enterEdit.mockResolvedValue('needs-window')
    qcDatastream.value = { id: 'mgd', name: 'Temp (QC)' }
    sourceDatastream.value = source
    const { wrapper, flow } = mountFlow()
    await flow.resume('mgd')
    await flushPromises()
    wrapper.findAllComponents(VDialog)[2].vm.$emit('update:modelValue', false)
    await flushPromises()
    expect(leaveEdit).toHaveBeenCalled()
    expect(present('window-stub')).toBe(false)
  })

  it('leaves the editor when the window is cancelled after a resume over committed-only sessions', async () => {
    enterEdit.mockResolvedValue('needs-window')
    qcDatastream.value = { id: 'mgd', name: 'Temp (QC)' }
    sourceDatastream.value = source
    sessions.value = [committed]
    const { wrapper, flow } = mountFlow()
    await flow.resume('mgd')
    await flushPromises()
    wrapper.findComponent(WindowStub).vm.$emit('cancel')
    await flushPromises()
    expect(leaveEdit).toHaveBeenCalled()
  })

  it('stays in the editor when the footer window is cancelled', async () => {
    qcDatastream.value = { id: 'mgd', name: 'Temp (QC)' }
    sourceDatastream.value = source
    const { wrapper, flow } = mountFlow()
    flow.openNewSession()
    await flushPromises()
    wrapper.findComponent(WindowStub).vm.$emit('cancel')
    await flushPromises()
    expect(leaveEdit).not.toHaveBeenCalled()
    expect(present('window-stub')).toBe(false)
  })

  it('starts the session in the open editor when a resume window is confirmed', async () => {
    enterEdit.mockResolvedValue('needs-window')
    qcDatastream.value = { id: 'mgd', name: 'Temp (QC)' }
    sourceDatastream.value = source
    const { wrapper, flow } = mountFlow()
    await flow.resume('mgd')
    await flushPromises()
    wrapper.findComponent(WindowStub).vm.$emit('confirm', window)
    await flushPromises()
    expect(startSessionOver).toHaveBeenCalledWith(window)
    expect(enterEdit).toHaveBeenCalledTimes(1)
  })

  it('keeps the window open to pick again when starting the session fails', async () => {
    startSessionOver.mockResolvedValue(false)
    qcDatastream.value = { id: 'mgd', name: 'Temp (QC)' }
    sourceDatastream.value = source
    const { wrapper, flow } = mountFlow()
    flow.openNewSession()
    await flushPromises()
    wrapper.findComponent(WindowStub).vm.$emit('confirm', window)
    await flushPromises()
    expect(present('window-stub')).toBe(true)
  })

  it('remounts the window step for a new target, so its defaults are fresh', async () => {
    const option = optionWith([committed])
    loadForSource.mockResolvedValue([option])
    // The entering start fails and reopens the step on the open editor.
    enterEdit.mockResolvedValue('needs-window')
    qcDatastream.value = { id: 'mgd', name: 'Temp (QC)' }
    sourceDatastream.value = source
    const { wrapper, flow } = mountFlow()
    await flow.openFor(source)
    await flushPromises()
    wrapper.findComponent(ChooserStub).vm.$emit('edit', option)
    await flushPromises()
    const first = wrapper.findComponent(WindowStub).vm

    wrapper.findComponent(WindowStub).vm.$emit('confirm', window)
    await flushPromises()

    expect(present('window-stub')).toBe(true)
    expect(wrapper.findComponent(WindowStub).vm).not.toBe(first)
  })

  it('closes the window when the start left the editor', async () => {
    startSessionOver.mockImplementation(async () => {
      qcDatastream.value = null
      return false
    })
    qcDatastream.value = { id: 'mgd', name: 'Temp (QC)' }
    sourceDatastream.value = source
    const { wrapper, flow } = mountFlow()
    flow.openNewSession()
    await flushPromises()
    wrapper.findComponent(WindowStub).vm.$emit('confirm', window)
    await flushPromises()
    expect(present('window-stub')).toBe(false)
  })

  it('leaves the editor when a resume needs a window but the source is missing', async () => {
    enterEdit.mockResolvedValue('needs-window')
    qcDatastream.value = { id: 'mgd', name: 'Temp (QC)' }
    sourceDatastream.value = null
    const { flow } = mountFlow()
    await flow.resume('mgd')
    await flushPromises()
    expect(leaveEdit).toHaveBeenCalled()
    expect(error).toHaveBeenCalled()
    expect(present('window-stub')).toBe(false)
  })

  it('starts a new session in the open editor from the footer', async () => {
    qcDatastream.value = { id: 'mgd', name: 'Temp (QC)' }
    sourceDatastream.value = source
    sessions.value = [committed]
    const { wrapper, flow } = mountFlow()
    flow.openNewSession()
    await flushPromises()
    wrapper.findComponent(WindowStub).vm.$emit('confirm', window)
    await flushPromises()
    expect(startSessionOver).toHaveBeenCalledWith(window)
    expect(enterEdit).not.toHaveBeenCalled()
    expect(present('window-stub')).toBe(false)
  })

  it('leaves the open session before the create form, not after the create', async () => {
    loadForSource.mockResolvedValue([])
    qcDatastream.value = { id: 'mgd', name: 'Temp (QC)' }
    const { flow } = mountFlow()
    await flow.openFor(source)
    await flushPromises()
    expect(closeEditor).toHaveBeenCalled()
    expect(present('create-stub')).toBe(true)
  })

  it('creates nothing when the open session is kept', async () => {
    loadForSource.mockResolvedValue([])
    closeEditor.mockResolvedValue(false)
    qcDatastream.value = { id: 'mgd', name: 'Temp (QC)' }
    const { wrapper, flow } = mountFlow()
    await flow.openFor(source)
    await flushPromises()
    expect(dialogOpen(wrapper, 1)).toBe(false)
    expect(createManaged).not.toHaveBeenCalled()
  })

  it('asks before the create form opened from the chooser', async () => {
    const option = optionWith([inProgress])
    loadForSource.mockResolvedValue([option])
    qcDatastream.value = { id: 'other', name: 'Other (QC)' }
    const { wrapper, flow } = mountFlow()
    await flow.openFor(source)
    await flushPromises()
    wrapper.findComponent(ChooserStub).vm.$emit('create')
    await flushPromises()
    expect(closeEditor).toHaveBeenCalled()
    expect(present('create-stub')).toBe(true)
  })

  it('returns to the chooser when the open session is kept', async () => {
    const option = optionWith([inProgress])
    loadForSource.mockResolvedValue([option])
    closeEditor.mockResolvedValue(false)
    qcDatastream.value = { id: 'other', name: 'Other (QC)' }
    const { wrapper, flow } = mountFlow()
    await flow.openFor(source)
    await flushPromises()
    wrapper.findComponent(ChooserStub).vm.$emit('create')
    await flushPromises()
    expect(dialogOpen(wrapper, 1)).toBe(false)
    expect(dialogOpen(wrapper, 0)).toBe(true)
  })

  it('does not ask when nothing is being edited', async () => {
    loadForSource.mockResolvedValue([])
    const { flow } = mountFlow()
    await flow.openFor(source)
    await flushPromises()
    expect(closeEditor).not.toHaveBeenCalled()
    expect(present('create-stub')).toBe(true)
  })

  it('asks for a window for a newly created managed datastream', async () => {
    loadForSource.mockResolvedValue([])
    const managed = { id: 'mgd-new', name: 'Temp (QC new)' }
    createManaged.mockResolvedValue({
      managedDatastream: managed,
      history: { id: 'h-new' },
    })
    const { wrapper, flow } = mountFlow()
    await flow.openFor(source)
    await flushPromises()
    wrapper
      .findComponent(CreateStub)
      .vm.$emit('confirm', {
        source,
        processingLevelId: 'pl',
        description: 'Cleaned series',
        sensorId: 'sn-1',
      })
    await flushPromises()

    expect(addQcHistory).toHaveBeenCalledWith({ id: 'h-new' })
    expect(datastreams.value).toContainEqual(managed)
    expect(success).toHaveBeenCalledWith('Managed datastream created.')
    // Closed dialogs keep their content mounted, so check the dialog itself.
    expect(dialogOpen(wrapper, 1)).toBe(false)
    expect(present('window-stub')).toBe(true)

    wrapper.findComponent(WindowStub).vm.$emit('confirm', window)
    await flushPromises()
    expect(enterEdit).toHaveBeenCalledWith('mgd-new', window, undefined)
  })
})
