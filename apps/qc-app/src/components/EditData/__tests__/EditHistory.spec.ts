import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'
// The per-operation comment textarea (Vuetify auto-grow) observes resizes.
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const editHistory = ref<any[]>([])
const selectedSeries = ref<any>(null)
const isUpdating = ref(false)
const redraw = vi.fn().mockResolvedValue(undefined)
const refreshGraphSeriesArray = vi.fn().mockResolvedValue(undefined)

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ editHistory, selectedSeries, isUpdating, redraw }),
}))

const qcDatastream = ref<any>(null)
vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ refreshGraphSeriesArray, qcDatastream }),
}))

const clearSelected = vi.fn().mockResolvedValue(undefined)
const setPlotSelection = vi.fn().mockResolvedValue(undefined)
vi.mock('@/composables/useDataSelection', () => ({
  useDataSelection: () => ({ clearSelected, setPlotSelection }),
}))

vi.mock('@uwrl/qc-utils', () => ({
  formatDuration: (ms: number) => String(ms) + 'ms',
  // operations.ts (transitively imported via EditHistory.vue's
  // `iconForMethod` lookup) reads enum values to build its method →
  // operation-id map. Stub the keys it actually consults; the test
  // never inspects the icon output, only that the entry renders.
  EnumEditOperations: {
    ADD_POINTS: 'ADD_POINTS',
    CHANGE_VALUES: 'CHANGE_VALUES',
    ASSIGN_VALUES_BULK: 'ASSIGN_VALUES_BULK',
    ASSIGN_DATETIMES_BULK: 'ASSIGN_DATETIMES_BULK',
    DELETE_POINTS: 'DELETE_POINTS',
    DRIFT_CORRECTION: 'DRIFT_CORRECTION',
    INTERPOLATE: 'INTERPOLATE',
    SHIFT_DATETIMES: 'SHIFT_DATETIMES',
    FILL_GAPS: 'FILL_GAPS',
  },
  EnumFilterOperations: {
    FIND_GAPS: 'FIND_GAPS',
    PERSISTENCE: 'PERSISTENCE',
    CHANGE: 'CHANGE',
    RATE_OF_CHANGE: 'RATE_OF_CHANGE',
    VALUE_THRESHOLD: 'VALUE_THRESHOLD',
    DATETIME_RANGE: 'DATETIME_RANGE',
    SELECTION: 'SELECTION',
  },
  Operator: {
    ADD: 'ADD',
    SUB: 'SUB',
    MULT: 'MULT',
    DIV: 'DIV',
    ASSIGN: 'ASSIGN',
  },
  TimeUnit: {
    SECOND: 's',
    MINUTE: 'm',
    HOUR: 'h',
    DAY: 'D',
    WEEK: 'W',
    MONTH: 'M',
    YEAR: 'Y',
  },
  LogicalOperation: {
    LT: 'Less than',
    LTE: 'Less than or equal to',
    GT: 'Greater than',
    GTE: 'Greater than or equal to',
    E: 'Equal',
  },
}))

import EditHistory from '@/components/EditData/EditHistory.vue'

function makeSeries(overrides: Partial<any> = {}) {
  return {
    data: {
      isLoading: false,
      loadingTime: 0,
      redoStack: [] as any[],
      history: [] as any[],
      undo: vi.fn().mockResolvedValue([1, 2]),
      redo: vi.fn().mockResolvedValue([]),
      reload: vi.fn().mockResolvedValue(undefined),
      reloadHistory: vi.fn().mockResolvedValue([3]),
      ...overrides,
    },
  }
}

/**
 * Build a `HistoryItem`-shaped object with a populated
 * `execution` record. Mirrors what `ObservationRecord.dispatch*`
 * would produce so the EditHistory template's
 * `entry.execution.inFlight` / `.status` / `.mode` / `.durationMs`
 * reads find the fields they expect. Callers pass any execution
 * overrides as a single object (e.g. `{ durationMs: 12 }`).
 */
function makeEntry(
  method: string,
  args: any[] = [],
  execution: Partial<{
    startedAt: number
    inFlight: boolean
    status: 'success' | 'failed'
    durationMs: number
    mode: 'worker' | 'inline'
    datasetSize: number
    selectionSize: number
  }> = {},
) {
  return {
    method,
    args,
    execution: {
      startedAt: 0,
      inFlight: false,
      ...execution,
    },
  }
}

function createWrapper(props: Record<string, unknown> = {}) {
  return mount(EditHistory, {
    props,
    global: { plugins: [createTestPinia(), createTestVuetify()] },
  })
}

describe('EditHistory.vue', () => {
  beforeEach(() => {
    editHistory.value = []
    isUpdating.value = false
    selectedSeries.value = makeSeries()
    vi.clearAllMocks()
  })

  it('disables undo/redo when history is empty', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('[data-testid="history-undo-btn"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('[data-testid="history-redo-btn"]').attributes('disabled')).toBeDefined()
  })

  it('disables undo with history when isUpdating is true', async () => {
    editHistory.value = [makeEntry('FOO')]
    isUpdating.value = true
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.find('[data-testid="history-undo-btn"]').attributes('disabled')).toBeDefined()
  })

  it('enables undo with at least one history entry', async () => {
    editHistory.value = [makeEntry('ADD_POINTS')]
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.find('[data-testid="history-undo-btn"]').attributes('disabled')).toBeUndefined()
  })

  it('enables redo when redoStack has entries', async () => {
    selectedSeries.value = makeSeries({ redoStack: [{ method: 'X' }] })
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.find('[data-testid="history-redo-btn"]').attributes('disabled')).toBeUndefined()
  })

  it('shows count chip when editCount > 0', async () => {
    const wrapper = createWrapper()
    editHistory.value = [makeEntry('A'), makeEntry('B')]
    await flushPromises()
    expect(wrapper.text()).toContain('2')
  })

  it('renders empty-state message when there are no edits', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('Edit operations will appear here.')
  })

  it('renders entries with formatted method labels', async () => {
    editHistory.value = [
      makeEntry('ADD_POINTS', [1, [1, 2, 3], { k: 'v' }, 'str'], { durationMs: 10 }),
      makeEntry('SHIFT_DATETIMES', [], { durationMs: 5 }),
    ]
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('Add Points')
    expect(wrapper.text()).toContain('Shift Datetimes')
    expect(wrapper.find('[data-testid="history-item-0"]').exists()).toBe(true)
  })

  it('expands and collapses the args drawer', async () => {
    editHistory.value = [
      makeEntry('ADD_POINTS', [[1, 2, 3, 4, 5, 6, 7], [], { a: 1 }, 42], { durationMs: 12 }),
    ]
    const wrapper = createWrapper()
    await flushPromises()
    const expandBtn = wrapper.find('[data-testid="history-item-0"] .edit-history__expand')
    await expandBtn.trigger('click')
    expect(wrapper.text()).toContain('Arguments')
    await expandBtn.trigger('click')
    expect(wrapper.text()).not.toContain('Arguments')
  })

  it('emits update:collapsed when header is clicked', async () => {
    const wrapper = createWrapper({ collapsible: true, collapsed: false })
    await wrapper.find('.edit-history__header').trigger('click')
    expect(wrapper.emitted('update:collapsed')).toBeTruthy()
  })

  it('does not emit update:collapsed when collapsible is false', async () => {
    const wrapper = createWrapper({ collapsible: false })
    await wrapper.find('.edit-history__header').trigger('click')
    expect(wrapper.emitted('update:collapsed')).toBeFalsy()
  })

  it('emits pop-out when pop-out button is clicked', async () => {
    const wrapper = createWrapper({ popOutEnabled: true })
    const popBtn = wrapper.find('[aria-label="Open history in a modal window"]')
    await popBtn.trigger('click')
    expect(wrapper.emitted('pop-out')).toBeTruthy()
  })
})

describe('EditHistory.vue actions', () => {
  beforeEach(() => {
    editHistory.value = []
    isUpdating.value = false
    selectedSeries.value = makeSeries()
    vi.clearAllMocks()
  })

  it('undo button calls undo and dispatches replayed selection', async () => {
    vi.useFakeTimers()
    editHistory.value = [makeEntry('ADD_POINTS')]
    const wrapper = createWrapper()
    await flushPromises()
    await wrapper.find('[data-testid="history-undo-btn"]').trigger('click')
    await vi.runAllTimersAsync()
    expect(selectedSeries.value.data.undo).toHaveBeenCalled()
    expect(setPlotSelection).toHaveBeenCalledWith([1, 2])
    vi.useRealTimers()
  })

  it('redo button clears selection when replay returns empty', async () => {
    vi.useFakeTimers()
    selectedSeries.value.data.redoStack = [{ method: 'X' }]
    selectedSeries.value.data.redo = vi.fn().mockResolvedValue([])
    const wrapper = createWrapper()
    await flushPromises()
    await wrapper.find('[data-testid="history-redo-btn"]').trigger('click')
    await vi.runAllTimersAsync()
    expect(selectedSeries.value.data.redo).toHaveBeenCalled()
    expect(clearSelected).toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('redo button dispatches selection when replay returns indices', async () => {
    vi.useFakeTimers()
    selectedSeries.value.data.redoStack = [{ method: 'X' }]
    selectedSeries.value.data.redo = vi.fn().mockResolvedValue([7, 8])
    const wrapper = createWrapper()
    await flushPromises()
    await wrapper.find('[data-testid="history-redo-btn"]').trigger('click')
    await vi.runAllTimersAsync()
    expect(setPlotSelection).toHaveBeenCalledWith([7, 8])
    vi.useRealTimers()
  })

  it('baseline reload button calls reload and refreshGraphSeriesArray', async () => {
    vi.useFakeTimers()
    const wrapper = createWrapper()
    await flushPromises()
    const reloadBtn = wrapper.findAll('button').find((b) => b.html().includes('mdi-reload'))
    expect(reloadBtn).toBeTruthy()
    await reloadBtn!.trigger('click')
    await vi.runAllTimersAsync()
    expect(selectedSeries.value.data.reload).toHaveBeenCalled()
    expect(refreshGraphSeriesArray).toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('per-step reload button calls reloadHistory with entry index', async () => {
    vi.useFakeTimers()
    editHistory.value = [makeEntry('ADD_POINTS')]
    selectedSeries.value.data.reloadHistory = vi.fn().mockResolvedValue([9])
    const wrapper = createWrapper()
    await flushPromises()
    const entry = wrapper.find('[data-testid="history-item-0"]')
    const reloadBtn = entry.findAll('button').find((b) => b.html().includes('mdi-reload'))
    expect(reloadBtn).toBeTruthy()
    await reloadBtn!.trigger('click')
    await vi.runAllTimersAsync()
    expect(selectedSeries.value.data.reloadHistory).toHaveBeenCalledWith(0)
    expect(setPlotSelection).toHaveBeenCalledWith([9])
    vi.useRealTimers()
  })

  it('Ctrl+Z on window triggers undo', async () => {
    vi.useFakeTimers()
    editHistory.value = [makeEntry('ADD_POINTS')]
    const undoSpy = selectedSeries.value.data.undo
    createWrapper()
    await flushPromises()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'z', ctrlKey: true }))
    await vi.runAllTimersAsync()
    expect(undoSpy).toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('Ctrl+Y on window triggers redo', async () => {
    vi.useFakeTimers()
    selectedSeries.value.data.redoStack = [{ method: 'X' }]
    const redoSpy = selectedSeries.value.data.redo
    createWrapper()
    await flushPromises()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'y', ctrlKey: true }))
    await vi.runAllTimersAsync()
    expect(redoSpy).toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('Ctrl+Shift+Z on window triggers redo', async () => {
    vi.useFakeTimers()
    selectedSeries.value.data.redoStack = [{ method: 'X' }]
    const redoSpy = selectedSeries.value.data.redo
    createWrapper()
    await flushPromises()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'z', ctrlKey: true, shiftKey: true }))
    await vi.runAllTimersAsync()
    expect(redoSpy).toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('ignores Ctrl+Z originating from an input element', async () => {
    vi.useFakeTimers()
    editHistory.value = [makeEntry('ADD_POINTS')]
    const undoSpy = selectedSeries.value.data.undo
    createWrapper()
    await flushPromises()
    const input = document.createElement('input')
    document.body.appendChild(input)
    const ev = new KeyboardEvent('keydown', { key: 'z', ctrlKey: true, bubbles: true })
    Object.defineProperty(ev, 'target', { value: input })
    window.dispatchEvent(ev)
    await vi.runAllTimersAsync()
    expect(undoSpy).not.toHaveBeenCalled()
    document.body.removeChild(input)
    vi.useRealTimers()
  })

  it('ignores keydown without modifier', async () => {
    vi.useFakeTimers()
    editHistory.value = [makeEntry('ADD_POINTS')]
    const undoSpy = selectedSeries.value.data.undo
    createWrapper()
    await flushPromises()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'z' }))
    await vi.runAllTimersAsync()
    expect(undoSpy).not.toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('header Enter key toggles collapsed', async () => {
    const wrapper = createWrapper({ collapsible: true, collapsed: false })
    await wrapper.find('.edit-history__header').trigger('keydown.enter')
    expect(wrapper.emitted('update:collapsed')).toBeTruthy()
  })

  // A committed session's operations are a record of what happened, not a
  // draft: nothing in the panel may rewrite them.
  describe('read-only session', () => {
    const readOnly = async () => {
      const { useQcSessionStore } = await import('@/store/qcSession')
      const store = useQcSessionStore()
      // `createdAt` is required: SessionList orders on it.
      store.sessions = [
        {
          id: 'a',
          status: 'committed',
          createdAt: '2025-01-01T00:00:00Z',
          phenomenonTimeStart: '2025-01-01T00:00:00Z',
          phenomenonTimeEnd: '2025-02-01T00:00:00Z',
        },
        {
          id: 'b',
          status: 'in_progress',
          createdAt: '2025-02-01T00:00:00Z',
          phenomenonTimeStart: '2025-02-01T00:00:00Z',
          phenomenonTimeEnd: '2025-03-01T00:00:00Z',
        },
      ] as any
      store.currentSessionId = 'b'
      store.viewedSessionId = 'a'
      return store
    }

    it('hides the per-entry undo and disables the toolbar undo/redo', async () => {
      editHistory.value = [{ method: 'ADD_POINTS', args: [], execution: {} }]
      selectedSeries.value = { data: { history: editHistory.value, redoStack: [{}] } }
      const w = createWrapper()
      await readOnly()
      await flushPromises()

      expect(w.find('[data-testid="history-undo-0"]').exists()).toBe(false)
      expect(
        w.find('[data-testid="history-undo-btn"]').attributes('disabled')
      ).toBeDefined()
      expect(
        w.find('[data-testid="history-redo-btn"]').attributes('disabled')
      ).toBeDefined()
      expect(
        w.find('[data-testid="history-load-btn"]').attributes('disabled')
      ).toBeDefined()
    })

    it('disables reload-from-server, which would wipe the record', async () => {
      editHistory.value = [{ method: 'ADD_POINTS', args: [], execution: {} }]
      selectedSeries.value = { data: { history: editHistory.value, redoStack: [] } }
      const w = createWrapper()
      await readOnly()
      await flushPromises()

      const baseline = w.find('.edit-history__row--baseline')
      expect(baseline.find('button').attributes('disabled')).toBeDefined()
    })

    it('keeps the entries below when reloading from a step', async () => {
      const history = [
        { method: 'SELECTION', args: [], execution: {} },
        { method: 'DELETE_POINTS', args: [], execution: {} },
        { method: 'INTERPOLATE', args: [], execution: {} },
      ]
      editHistory.value = history
      // Stand in for the engine: truncate to `0..index`, as qc-utils does.
      const reloadHistory = vi.fn(async (index: number) => {
        history.splice(index + 1)
        return []
      })
      selectedSeries.value = { data: { history, redoStack: [], reloadHistory } }

      const w = createWrapper()
      await readOnly()
      await flushPromises()

      await w.find('[data-testid="history-item-0"]').findAll('button').at(-1)!.trigger('click')
      await vi.waitFor(() => expect(reloadHistory).toHaveBeenCalledWith(0))

      // Data stepped back, but the record of what the session did survives.
      // Polled: the restore runs after an await inside the handler's timeout.
      await vi.waitFor(() =>
        expect(history.map((h) => h.method)).toEqual([
          'SELECTION',
          'DELETE_POINTS',
          'INTERPOLATE',
        ])
      )
    })
  })

  describe('loaded step', () => {
    it('marks the step the plot reflects, and clears it on undo', async () => {
      const history = [
        { method: 'SELECTION', args: [], execution: {} },
        { method: 'DELETE_POINTS', args: [], execution: {} },
      ]
      editHistory.value = history
      const reloadHistory = vi.fn(async () => [])
      const undo = vi.fn(async () => [])
      selectedSeries.value = { data: { history, redoStack: [], reloadHistory, undo } }

      const w = createWrapper()
      await flushPromises()
      // With no step singled out the plot reflects the whole history, so the
      // last entry carries the marker.
      expect(w.find('[data-testid="history-loaded-1"]').exists()).toBe(true)
      expect(w.find('[data-testid="history-loaded-0"]').exists()).toBe(false)

      await w.find('[data-testid="history-item-0"]').findAll('button').at(-1)!.trigger('click')
      await vi.waitFor(() =>
        expect(w.find('[data-testid="history-loaded-0"]').exists()).toBe(true)
      )

      // Undoing changes the history, so "showing step 0" no longer holds and
      // the marker returns to the end of the list.
      // Wait for the step reload to settle: the button is disabled while
      // `isUpdating`, and a click on a disabled button never reaches the handler.
      await vi.waitFor(() => expect(isUpdating.value).toBe(false))
      await w.find('[data-testid="history-undo-btn"]').trigger('click')
      await vi.waitFor(() =>
        expect(w.find('[data-testid="history-loaded-0"]').exists()).toBe(false)
      )
      expect(w.find('[data-testid="history-loaded-1"]').exists()).toBe(true)
    })
  })

  describe('session switch', () => {
    it('shows a loading state instead of the outgoing session operations', async () => {
      editHistory.value = [{ method: 'ADD_POINTS', args: [], execution: {} }]
      selectedSeries.value = { data: { history: editHistory.value, redoStack: [] } }
      const w = createWrapper()
      await flushPromises()
      expect(w.find('[data-testid="history-item-0"]').exists()).toBe(true)

      const { useQcSessionStore } = await import('@/store/qcSession')
      useQcSessionStore().isSwitchingSession = true
      await flushPromises()

      expect(w.find('[data-testid="history-loading"]').exists()).toBe(true)
      expect(w.find('[data-testid="history-item-0"]').exists()).toBe(false)
    })
  })

  describe('shown step fallback', () => {
    it('marks nothing when the history is empty', async () => {
      editHistory.value = []
      selectedSeries.value = { data: { history: [], redoStack: [] } }
      const w = createWrapper()
      await flushPromises()
      expect(w.find('[data-testid^="history-loaded-"]').exists()).toBe(false)
    })

    it('falls back to the last entry when the chosen step is out of range', async () => {
      const history = [
        { method: 'SELECTION', args: [], execution: {} },
        { method: 'DELETE_POINTS', args: [], execution: {} },
        { method: 'INTERPOLATE', args: [], execution: {} },
      ]
      editHistory.value = history
      const reloadHistory = vi.fn(async () => [])
      selectedSeries.value = { data: { history, redoStack: [], reloadHistory } }
      const w = createWrapper()
      await flushPromises()

      await w.find('[data-testid="history-item-2"]').findAll('button').at(-2)!.trigger('click')
      await vi.waitFor(() =>
        expect(w.find('[data-testid="history-loaded-2"]').exists()).toBe(true)
      )

      // The history shrinks under the chosen step. Splice through the ref's
      // proxy: mutating the raw array wouldn't trigger reactivity.
      editHistory.value.splice(1)
      await flushPromises()
      expect(w.find('[data-testid="history-loaded-0"]').exists()).toBe(true)
    })
  })

  describe('attribution', () => {
    it('shows who applied an operation, on the row and in the detail', async () => {
      editHistory.value = [
        { method: 'ADD_POINTS', args: [], execution: {}, performedBy: 'Ada Lovelace' },
        { method: 'DELETE_POINTS', args: [], execution: {} },
      ]
      selectedSeries.value = { data: { history: editHistory.value, redoStack: [] } }
      const w = createWrapper()
      await flushPromises()

      expect(w.find('[data-testid="history-author-0"]').text()).toBe('Ada Lovelace')
      // Unsaved operations have no server attribution yet.
      expect(w.find('[data-testid="history-author-1"]').exists()).toBe(false)

      await w.find('[data-testid="history-item-0"]').find('button').trigger('click')
      await flushPromises()
      expect(w.find('[data-testid="history-author-detail-0"]').text()).toContain(
        'Applied by Ada Lovelace'
      )
    })
  })

  describe('selection after loading a step', () => {
    const stepBackTo = async (returned: number[] | undefined) => {
      const history = [
        { method: 'SELECTION', args: [], execution: {} },
        { method: 'DELETE_POINTS', args: [], execution: {} },
      ]
      editHistory.value = history
      const reloadHistory = vi.fn(async () => returned as any)
      selectedSeries.value = { data: { history, redoStack: [], reloadHistory } }
      const w = createWrapper()
      await flushPromises()
      // Item 0 isn't the trailing entry, so its buttons are expand + reload.
      await w.find('[data-testid="history-item-0"]').findAll('button').at(-1)!.trigger('click')
      await vi.waitFor(() => expect(reloadHistory).toHaveBeenCalledWith(0))
      await vi.waitFor(() => expect(isUpdating.value).toBe(false))
      await flushPromises()
    }

    it('applies the selection the replay produced', async () => {
      await stepBackTo([3, 4, 5])
      expect(setPlotSelection).toHaveBeenCalledWith([3, 4, 5])
      expect(clearSelected).not.toHaveBeenCalled()
    })

    // Without this the previous selection stayed painted on the plot.
    it('clears the selection when the replay produced none', async () => {
      await stepBackTo(undefined)
      expect(setPlotSelection).not.toHaveBeenCalled()
      expect(clearSelected).toHaveBeenCalledWith({ recordHistory: false })
    })

    it('clears the selection when the replay produced an empty one', async () => {
      await stepBackTo([])
      expect(setPlotSelection).not.toHaveBeenCalled()
      expect(clearSelected).toHaveBeenCalledWith({ recordHistory: false })
    })
  })
})
