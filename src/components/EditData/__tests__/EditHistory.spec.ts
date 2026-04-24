import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const editHistory = ref<any[]>([])
const selectedSeries = ref<any>(null)
const isUpdating = ref(false)
const redraw = vi.fn().mockResolvedValue(undefined)
const refreshGraphSeriesArray = vi.fn().mockResolvedValue(undefined)

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ editHistory, selectedSeries, isUpdating, redraw }),
}))

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ refreshGraphSeriesArray }),
}))

const clearSelected = vi.fn().mockResolvedValue(undefined)
const dispatchSelection = vi.fn().mockResolvedValue(undefined)
vi.mock('@/composables/useDataSelection', () => ({
  useDataSelection: () => ({ clearSelected, dispatchSelection }),
}))

vi.mock('@uwrl/qc-utils', () => ({
  formatDuration: (ms: number) => String(ms) + 'ms',
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
    editHistory.value = [{ method: 'FOO', args: [] }]
    isUpdating.value = true
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.find('[data-testid="history-undo-btn"]').attributes('disabled')).toBeDefined()
  })

  it('enables undo with at least one history entry', async () => {
    editHistory.value = [{ method: 'ADD_POINTS', args: [] }]
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
    editHistory.value = [{ method: 'A', args: [] }, { method: 'B', args: [] }]
    await flushPromises()
    expect(wrapper.text()).toContain('2')
  })

  it('renders empty-state message when there are no edits', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('Edit operations will appear here.')
  })

  it('renders entries with formatted method labels', async () => {
    editHistory.value = [
      { method: 'ADD_POINTS', args: [1, [1, 2, 3], { k: 'v' }, 'str'], duration: 10, icon: 'mdi-plus' },
      { method: 'SHIFT_DATETIMES', args: [], duration: 5 },
    ]
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('Add Points')
    expect(wrapper.text()).toContain('Shift Datetimes')
    expect(wrapper.find('[data-testid="history-item-0"]').exists()).toBe(true)
  })

  it('expands and collapses the args drawer', async () => {
    editHistory.value = [
      { method: 'ADD_POINTS', args: [[1, 2, 3, 4, 5, 6, 7], [], { a: 1 }, 42], duration: 12 },
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
    editHistory.value = [{ method: 'ADD_POINTS', args: [] }]
    const wrapper = createWrapper()
    await flushPromises()
    await wrapper.find('[data-testid="history-undo-btn"]').trigger('click')
    await vi.runAllTimersAsync()
    expect(selectedSeries.value.data.undo).toHaveBeenCalled()
    expect(dispatchSelection).toHaveBeenCalledWith([1, 2])
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
    expect(clearSelected).toHaveBeenCalledWith({ dispatchFilter: false })
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
    expect(dispatchSelection).toHaveBeenCalledWith([7, 8])
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
    editHistory.value = [{ method: 'ADD_POINTS', args: [] }]
    selectedSeries.value.data.reloadHistory = vi.fn().mockResolvedValue([9])
    const wrapper = createWrapper()
    await flushPromises()
    const entry = wrapper.find('[data-testid="history-item-0"]')
    const reloadBtn = entry.findAll('button').find((b) => b.html().includes('mdi-reload'))
    expect(reloadBtn).toBeTruthy()
    await reloadBtn!.trigger('click')
    await vi.runAllTimersAsync()
    expect(selectedSeries.value.data.reloadHistory).toHaveBeenCalledWith(0)
    expect(dispatchSelection).toHaveBeenCalledWith([9])
    vi.useRealTimers()
  })

  it('Ctrl+Z on window triggers undo', async () => {
    vi.useFakeTimers()
    editHistory.value = [{ method: 'ADD_POINTS', args: [] }]
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
    editHistory.value = [{ method: 'ADD_POINTS', args: [] }]
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
    editHistory.value = [{ method: 'ADD_POINTS', args: [] }]
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
})
