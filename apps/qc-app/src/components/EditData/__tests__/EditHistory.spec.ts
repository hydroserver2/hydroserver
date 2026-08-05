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

const toggleSnapshot = vi.fn().mockResolvedValue(undefined)
const plottedSnapshots = ref<string[]>([])
const isBuilding = ref(false)
vi.mock('@/composables/useHistorySnapshots', () => ({
  useHistorySnapshots: () => ({
    toggleSnapshot,
    isSnapshotPlotted: (sessionId: string, opIndex: number) =>
      plottedSnapshots.value.includes(`${sessionId}:${opIndex}`),
    isBuilding,
  }),
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

    /**
     * Stands in for the real `reloadHistory`: truncate to `0..index` and
     * replace the survivors with freshly dispatched entries carrying the
     * timings the replay just measured. Splices through the ref's proxy;
     * mutating the raw array wouldn't trigger reactivity.
     */
    const replayingReloadHistory = () =>
      vi.fn(async (index: number) => {
        const fresh = editHistory.value.slice(0, index + 1).map((h, i) => ({
          method: h.method,
          args: h.args,
          execution: { inFlight: false, status: 'success', durationMs: 900 + i },
        }))
        editHistory.value.splice(0, editHistory.value.length, ...fresh)
        return []
      })

    // The committed-session path restores the full operation list after the
    // replay so the user can keep stepping through it. That restore must not
    // drag the pre-replay timings back with it.
    it('shows the timings the replay produced, not the originals', async () => {
      const history = [
        makeEntry('SELECTION', [], { durationMs: 10 }),
        makeEntry('DELETE_POINTS', [], { durationMs: 20 }),
        makeEntry('INTERPOLATE', [], { durationMs: 30 }),
      ]
      editHistory.value = history
      selectedSeries.value = {
        data: {
          history: editHistory.value,
          redoStack: [],
          reloadHistory: replayingReloadHistory(),
        },
      }
      const w = createWrapper()
      await readOnly()
      await flushPromises()

      await w
        .find('[data-testid="history-item-1"]')
        .findAll('button')
        .at(-1)!
        .trigger('click')
      // `loadedStepIndex` moves synchronously, so waiting on the marker
      // would race the replay. Wait for the dispatch itself to settle.
      await vi.waitFor(() => expect(isUpdating.value).toBe(false))
      await flushPromises()

      // Replayed entries report the new measurement.
      expect(w.find('[data-testid="history-duration-0"]').text()).toContain('900')
      expect(w.find('[data-testid="history-duration-1"]').text()).toContain('901')
      // The un-replayed tail survives on screen but did not run.
      expect(w.findAll('[data-testid^="history-item-"]').length).toBe(3)
      expect(w.find('[data-testid="history-duration-2"]').exists()).toBe(false)
    })

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

      expect(
        w.find('[data-testid="history-reload-btn"]').attributes('disabled')
      ).toBeDefined()
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

    // Reloading from a step un-applies everything below it. A committed
    // session keeps those rows on screen, so their telemetry would otherwise
    // still advertise a run that no longer holds in this view.
    it('drops execution info for steps after the one being shown', async () => {
      const history = [
        makeEntry('SELECTION', [], { durationMs: 10 }),
        makeEntry('DELETE_POINTS', [], { durationMs: 20, status: 'failed' }),
        makeEntry('INTERPOLATE', [], { durationMs: 30 }),
      ]
      editHistory.value = history
      const reloadHistory = vi.fn(async () => [])
      selectedSeries.value = { data: { history, redoStack: [], reloadHistory } }

      const w = createWrapper()
      await flushPromises()
      expect(w.find('[data-testid="history-duration-2"]').exists()).toBe(true)
      expect(w.find('[data-testid="history-failed-1"]').exists()).toBe(true)

      await w
        .find('[data-testid="history-item-0"]')
        .findAll('button')
        .at(-1)!
        .trigger('click')
      await vi.waitFor(() =>
        expect(w.find('[data-testid="history-loaded-0"]').exists()).toBe(true)
      )

      // The step you reloaded from did run, so it keeps its label.
      expect(w.find('[data-testid="history-duration-0"]').exists()).toBe(true)
      expect(w.find('[data-testid="history-duration-1"]').exists()).toBe(false)
      expect(w.find('[data-testid="history-duration-2"]').exists()).toBe(false)
      // The failure badge is execution state too, so it goes as well.
      expect(w.find('[data-testid="history-failed-1"]').exists()).toBe(false)
    })
  })

  describe('execution telemetry placement', () => {
    // Duration stays on the row: it is the answer to "did that step run?",
    // which you want without expanding. Only the dev-only mode chip moved.
    it('keeps the duration on the row and the mode chip off it', async () => {
      editHistory.value = [
        makeEntry('SELECTION', [], { durationMs: 1234, mode: 'inline' }),
      ]
      const w = createWrapper()
      await flushPromises()

      const row = w.find('[data-testid="history-item-0"] .edit-history__row')
      expect(row.find('[data-testid="history-duration-0"]').exists()).toBe(true)
      expect(row.text()).not.toContain('inline')
    })

    it('shows the mode chip in the expanded drawer', async () => {
      editHistory.value = [
        makeEntry('SELECTION', [], { durationMs: 1234, mode: 'inline' }),
      ]
      const w = createWrapper()
      await flushPromises()

      await w
        .find('[data-testid="history-item-0"] .edit-history__expand')
        .trigger('click')
      await flushPromises()

      const detail = w.find('[data-testid="history-execution-0"]')
      expect(detail.exists()).toBe(true)
      expect(detail.text()).toContain('inline')
    })

    // A replayed step can measure well under a millisecond, which rounds to
    // "0ms". That is still a real run and must not read as "never ran".
    it('renders sub-millisecond and zero durations rather than hiding them', async () => {
      editHistory.value = [
        makeEntry('SELECTION', [], { durationMs: 0.0054 }),
        makeEntry('DELETE_POINTS', [], { durationMs: 0 }),
      ]
      const w = createWrapper()
      await flushPromises()

      expect(w.find('[data-testid="history-duration-0"]').exists()).toBe(true)
      expect(w.find('[data-testid="history-duration-1"]').exists()).toBe(true)
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

describe('EditHistory.vue snapshot buttons', () => {
  beforeEach(() => {
    editHistory.value = []
    isUpdating.value = false
    isBuilding.value = false
    plottedSnapshots.value = []
    selectedSeries.value = makeSeries()
    vi.clearAllMocks()
  })

  const makeSession = (id: string, createdAt = '2026-03-01T00:00:00Z') => ({
    id,
    createdAt,
    status: 'in_progress',
    phenomenonTimeStart: '2026-03-01T00:00:00Z',
    phenomenonTimeEnd: '2026-04-01T00:00:00Z',
  })

  /**
   * SessionList only renders the operations slot for a session it actually
   * lists, or in its no-session fallback. Seed `sessions` accordingly or the
   * history rows never mount.
   */
  const mountWithSession = async (
    sessionId: string | null,
    sessions: unknown[] = sessionId ? [makeSession(sessionId)] : []
  ) => {
    const pinia = createTestPinia()
    const { useQcSessionStore } = await import('@/store/qcSession')
    const store = useQcSessionStore()
    store.sessions = sessions as any
    store.viewedSessionId = sessionId
    return mount(EditHistory, {
      props: {},
      global: { plugins: [pinia, createTestVuetify()] },
    })
  }

  it('renders an add-to-plot button on each operation row and the baseline', async () => {
    editHistory.value = [makeEntry('FILL_GAPS'), makeEntry('DELETE_POINTS')]

    const w = await mountWithSession('sess-1')

    expect(w.find('[data-testid="history-snapshot-baseline"]').exists()).toBe(true)
    expect(w.find('[data-testid="history-snapshot-0"]').exists()).toBe(true)
    expect(w.find('[data-testid="history-snapshot-1"]').exists()).toBe(true)
  })

  it('toggles the snapshot for the clicked operation', async () => {
    editHistory.value = [makeEntry('FILL_GAPS')]

    const w = await mountWithSession('sess-1')
    await w.find('[data-testid="history-snapshot-0"]').trigger('click')

    expect(toggleSnapshot).toHaveBeenCalledWith('sess-1', 0)
  })

  it('toggles the baseline snapshot at index -1', async () => {
    editHistory.value = [makeEntry('FILL_GAPS')]

    const w = await mountWithSession('sess-1')
    await w.find('[data-testid="history-snapshot-baseline"]').trigger('click')

    expect(toggleSnapshot).toHaveBeenCalledWith('sess-1', -1)
  })

  // Plotting a comparison line is a read action, so it stays available on a
  // committed session, which is exactly when comparing matters most.
  it('stays enabled while the viewed session is read-only', async () => {
    editHistory.value = [makeEntry('FILL_GAPS')]

    const w = await mountWithSession('sess-1', [
      makeSession('sess-1'),
      makeSession('sess-2', '2026-04-01T00:00:00Z'),
    ])
    const { useQcSessionStore } = await import('@/store/qcSession')
    const store = useQcSessionStore()
    store.currentSessionId = 'sess-2'
    await flushPromises()

    expect(store.isReadOnly).toBe(true)
    expect(
      w.find('[data-testid="history-snapshot-0"]').attributes('disabled')
    ).toBeUndefined()
  })

  it('does nothing when no session is being viewed', async () => {
    editHistory.value = [makeEntry('FILL_GAPS')]

    const w = await mountWithSession(null)
    await w.find('[data-testid="history-snapshot-0"]').trigger('click')

    expect(toggleSnapshot).not.toHaveBeenCalled()
  })
})
