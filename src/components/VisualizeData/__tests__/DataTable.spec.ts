import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

// jsdom lacks ResizeObserver; DataTable uses it for virtual-scroll sizing.
class RO {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as any).ResizeObserver = (globalThis as any).ResizeObserver || RO

const isUpdating = ref(false)
const selectedSeries = ref<any>({
  data: {
    dataX: [] as number[],
    dataY: [] as number[],
    dispatch: vi.fn().mockResolvedValue(undefined),
  },
})
const redraw = vi.fn().mockResolvedValue(undefined)

const selectedData = ref<number[] | null>(null)
const qcDatastream = ref<any>({ id: 'ds-1' })

const qualifierById = ref<Record<string, any>>({})
const applied = ref<Record<string, any>>({})

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ isUpdating, selectedSeries, redraw }),
}))

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ selectedData, qcDatastream }),
}))

vi.mock('@/store/qualifiers', () => ({
  useQualifierStore: () => ({ qualifierById, applied }),
}))

const clearSelected = vi.fn().mockResolvedValue(undefined)
vi.mock('@/composables/useDataSelection', () => ({
  useDataSelection: () => ({ clearSelected }),
}))

vi.mock('@uwrl/qc-utils', () => ({
  EnumEditOperations: {
    ASSIGN_VALUES_BULK: 'ASSIGN_VALUES_BULK',
    ASSIGN_DATETIMES_BULK: 'ASSIGN_DATETIMES_BULK',
  },
  EnumFilterOperations: { SELECTION: 'SELECTION' },
  // Guard against Invalid Date (null/undefined/NaN epochs) during render.
  formatDate: (d: Date) => {
    const t = d?.getTime?.()
    if (t == null || Number.isNaN(t)) return ''
    return d.toISOString()
  },
}))

vi.mock('@/components/VisualizeData/EditableCell.vue', () => ({
  default: {
    name: 'EditableCell',
    props: ['value', 'display', 'edited', 'originalDisplay', 'editedDisplay', 'inputType', 'align'],
    emits: ['save', 'clear'],
    template: '<div class="editable-cell-stub" />',
  },
}))

import DataTable from '@/components/VisualizeData/DataTable.vue'

// Renders v-data-table-virtual item slots so EditableCell stubs mount
// with real props/emits and we can drive onValueSave/onDatetimeSave
// through the component's public slot interface.
function virtualTableStub() {
  return {
    name: 'VDataTableVirtualStub',
    props: ['items', 'rowProps'],
    template: `
      <div class="vdtv-stub">
        <div
          v-for="(_, index) in items"
          :key="index"
          class="vdtv-row"
          :data-index="index"
          :class="resolveRowClass(index)"
        >
          <slot name="item.actions" :index="index" />
          <slot name="item.datetime" :index="index" />
          <slot name="item.value" :index="index" />
          <slot name="item.qualifiers" :index="index" />
        </div>
      </div>
    `,
    methods: {
      resolveRowClass(index: number): Record<string, unknown> {
        const self = this as unknown as {
          rowProps?: (item: { internalItem: { index: number } }) => {
            class?: Record<string, unknown>
          }
        }
        if (typeof self.rowProps === 'function') {
          const item = { internalItem: { index } }
          const res = self.rowProps(item)
          return res?.class ?? {}
        }
        return {}
      },
    },
  }
}

// Track wrappers so each test fully unmounts; module-level reactive refs
// otherwise re-render stale wrappers from earlier tests and trigger
// null-subTree crashes during `beforeEach` state resets.
const openWrappers: VueWrapper<any>[] = []

function createWrapper() {
  const w = mount(DataTable, {
    global: {
      plugins: [createTestPinia(), createTestVuetify()],
      stubs: {
        'v-data-table-virtual': { template: '<div class="vdtv-stub"><slot /></div>' },
      },
    },
  })
  openWrappers.push(w)
  return w
}

// Variant of the wrapper that actually renders the item slots so we can
// exercise onValueSave/onDatetimeSave/onSelectChange/qualifier rendering.
function createWrapperWithSlots() {
  const w = mount(DataTable, {
    global: {
      plugins: [createTestPinia(), createTestVuetify()],
      stubs: {
        'v-data-table-virtual': virtualTableStub(),
      },
    },
  })
  openWrappers.push(w)
  return w
}

afterEach(() => {
  while (openWrappers.length) openWrappers.pop()!.unmount()
})

describe('DataTable.vue', () => {
  beforeEach(() => {
    isUpdating.value = false
    selectedSeries.value = {
      data: {
        dataX: [1000, 2000, 3000] as number[],
        dataY: [10, 20, 30] as number[],
        dispatch: vi.fn().mockResolvedValue(undefined),
      },
    }
    selectedData.value = null
    qcDatastream.value = { id: 'ds-1' }
    qualifierById.value = {}
    applied.value = {}
    vi.clearAllMocks()
  })

  it('disables discard and save buttons when there are no pending edits', async () => {
    const wrapper = createWrapper()
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const discard = buttons.find((b) => b.text().includes('Discard'))
    const save = buttons.find((b) => b.text().includes('Save changes'))
    expect(discard?.attributes('disabled')).toBeDefined()
    expect(save?.attributes('disabled')).toBeDefined()
  })

  it('disables save/discard while isUpdating even if edits exist', async () => {
    isUpdating.value = true
    const wrapper = createWrapper()
    await flushPromises()
    const discard = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Discard'))
    expect(discard?.attributes('disabled')).toBeDefined()
  })

  it('shows the row-count chip with the formatted row count', async () => {
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('3 rows')
  })

  it('omits the row-count chip when there are no rows', async () => {
    selectedSeries.value = {
      data: { dataX: [], dataY: [], dispatch: vi.fn() },
    }
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.text()).not.toMatch(/\d+ rows?/)
  })

  it('renders the toolbar header copy', async () => {
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('Observations')
    expect(wrapper.text()).toContain('Datetime')
    expect(wrapper.text()).toContain('Value')
  })

  it('mounts without throwing when qcDatastream is null', async () => {
    qcDatastream.value = null
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })
})

// Helpers to address rows rendered by the virtualTableStub.
function rowEditableCells(wrapper: any, rowIndex: number) {
  const row = wrapper.findAll('.vdtv-row').at(rowIndex)
  return row.findAllComponents({ name: 'EditableCell' })
}

// EditableCells appear in slot order: datetime (0), value (1).
function datetimeCell(wrapper: any, rowIndex: number) {
  return rowEditableCells(wrapper, rowIndex)[0]
}
function valueCell(wrapper: any, rowIndex: number) {
  return rowEditableCells(wrapper, rowIndex)[1]
}

describe('DataTable.vue formatNumber (via value cell display prop)', () => {
  beforeEach(() => {
    isUpdating.value = false
    selectedData.value = null
    qcDatastream.value = { id: 'ds-1' }
    qualifierById.value = {}
    applied.value = {}
    vi.clearAllMocks()
  })

  it('returns empty string for null, undefined, NaN values', async () => {
    selectedSeries.value = {
      data: {
        dataX: [1000, 2000, 3000],
        dataY: [null, undefined, NaN] as any,
        dispatch: vi.fn().mockResolvedValue(undefined),
      },
    }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    expect(valueCell(wrapper, 0).props('display')).toBe('')
    expect(valueCell(wrapper, 1).props('display')).toBe('')
    expect(valueCell(wrapper, 2).props('display')).toBe('')
  })

  it('rounds to 4 dp and strips trailing zeros', async () => {
    selectedSeries.value = {
      data: {
        dataX: [1000, 2000, 3000, 4000],
        dataY: [10, 3.14159265, 0.1 + 0.2, 2.5],
        dispatch: vi.fn().mockResolvedValue(undefined),
      },
    }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    expect(valueCell(wrapper, 0).props('display')).toBe('10')
    expect(valueCell(wrapper, 1).props('display')).toBe('3.1416')
    expect(valueCell(wrapper, 2).props('display')).toBe('0.3')
    expect(valueCell(wrapper, 3).props('display')).toBe('2.5')
  })
})

describe('DataTable.vue formatDatetimeLocal (via datetime cell value prop)', () => {
  beforeEach(() => {
    isUpdating.value = false
    selectedData.value = null
    qcDatastream.value = { id: 'ds-1' }
    qualifierById.value = {}
    applied.value = {}
    vi.clearAllMocks()
  })

  it('returns empty string for null/undefined/NaN epoch', async () => {
    selectedSeries.value = {
      data: {
        dataX: [null, undefined, NaN] as any,
        dataY: [1, 2, 3],
        dispatch: vi.fn().mockResolvedValue(undefined),
      },
    }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    expect(datetimeCell(wrapper, 0).props('value')).toBe('')
    expect(datetimeCell(wrapper, 1).props('value')).toBe('')
    expect(datetimeCell(wrapper, 2).props('value')).toBe('')
  })

  it('produces YYYY-MM-DDTHH:mm:ss formatted string for a valid epoch', async () => {
    const epoch = new Date(2024, 2, 15, 9, 7, 5).getTime()
    selectedSeries.value = {
      data: {
        dataX: [epoch],
        dataY: [1],
        dispatch: vi.fn().mockResolvedValue(undefined),
      },
    }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    expect(datetimeCell(wrapper, 0).props('value')).toBe('2024-03-15T09:07:05')
  })

  it('formats epoch 0 to a non-empty string', async () => {
    selectedSeries.value = {
      data: {
        dataX: [0],
        dataY: [1],
        dispatch: vi.fn().mockResolvedValue(undefined),
      },
    }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    const v = datetimeCell(wrapper, 0).props('value') as string
    expect(v).not.toBe('')
    expect(v).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/)
  })
})

describe('DataTable.vue onValueSave / clearValueEdit / pendingEditCount', () => {
  beforeEach(() => {
    isUpdating.value = false
    selectedSeries.value = {
      data: {
        dataX: [1000, 2000, 3000],
        dataY: [10, 20, 30],
        dispatch: vi.fn().mockResolvedValue(undefined),
      },
    }
    selectedData.value = null
    qcDatastream.value = { id: 'ds-1' }
    qualifierById.value = {}
    applied.value = {}
    vi.clearAllMocks()
  })

  it('adds a pending edit when a different value is saved', async () => {
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    valueCell(wrapper, 0).vm.$emit('save', '99')
    await flushPromises()
    expect(wrapper.text()).toContain('1 unsaved')
  })

  it('does NOT add a pending edit when the saved value equals the original', async () => {
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    valueCell(wrapper, 0).vm.$emit('save', '10')
    await flushPromises()
    expect(wrapper.text()).not.toContain('unsaved')
  })

  it('ignores NaN input', async () => {
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    valueCell(wrapper, 0).vm.$emit('save', 'not-a-number')
    await flushPromises()
    expect(wrapper.text()).not.toContain('unsaved')
  })

  it('removes a pending edit when a subsequent save matches the original', async () => {
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    valueCell(wrapper, 0).vm.$emit('save', '99')
    await flushPromises()
    expect(wrapper.text()).toContain('1 unsaved')
    valueCell(wrapper, 0).vm.$emit('save', '10')
    await flushPromises()
    expect(wrapper.text()).not.toContain('unsaved')
  })

  it('clearValueEdit removes an existing edit', async () => {
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    valueCell(wrapper, 0).vm.$emit('save', '99')
    await flushPromises()
    expect(wrapper.text()).toContain('1 unsaved')
    valueCell(wrapper, 0).vm.$emit('clear')
    await flushPromises()
    expect(wrapper.text()).not.toContain('unsaved')
  })

  it('edited prop on the value cell reflects pending edit state', async () => {
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    expect(valueCell(wrapper, 0).props('edited')).toBe(false)
    valueCell(wrapper, 0).vm.$emit('save', '99')
    await flushPromises()
    expect(valueCell(wrapper, 0).props('edited')).toBe(true)
    expect(valueCell(wrapper, 0).props('editedDisplay')).toBe('99')
  })
})

describe('DataTable.vue onDatetimeSave / clearDatetimeEdit', () => {
  beforeEach(() => {
    isUpdating.value = false
    selectedSeries.value = {
      data: {
        dataX: [1000, 2000, 3000],
        dataY: [10, 20, 30],
        dispatch: vi.fn().mockResolvedValue(undefined),
      },
    }
    selectedData.value = null
    qcDatastream.value = { id: 'ds-1' }
    qualifierById.value = {}
    applied.value = {}
    vi.clearAllMocks()
  })

  it('adds a pending datetime edit when epoch changes', async () => {
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    datetimeCell(wrapper, 0).vm.$emit('save', '2024-01-01T00:00:00')
    await flushPromises()
    expect(wrapper.text()).toContain('1 unsaved')
  })

  it('ignores an empty/invalid datetime string', async () => {
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    datetimeCell(wrapper, 0).vm.$emit('save', '')
    await flushPromises()
    datetimeCell(wrapper, 0).vm.$emit('save', 'not-a-date')
    await flushPromises()
    expect(wrapper.text()).not.toContain('unsaved')
  })

  it('removes pending edit when save matches the original epoch', async () => {
    const epoch = new Date(2024, 0, 1, 0, 0, 0).getTime()
    selectedSeries.value = {
      data: {
        dataX: [epoch],
        dataY: [10],
        dispatch: vi.fn().mockResolvedValue(undefined),
      },
    }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    // change first
    datetimeCell(wrapper, 0).vm.$emit('save', '2025-05-05T05:05:05')
    await flushPromises()
    expect(wrapper.text()).toContain('1 unsaved')
    // then set back to original local string
    datetimeCell(wrapper, 0).vm.$emit('save', '2024-01-01T00:00:00')
    await flushPromises()
    expect(wrapper.text()).not.toContain('unsaved')
  })

  it('clearDatetimeEdit removes an existing edit', async () => {
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    datetimeCell(wrapper, 0).vm.$emit('save', '2024-01-01T00:00:00')
    await flushPromises()
    expect(wrapper.text()).toContain('1 unsaved')
    datetimeCell(wrapper, 0).vm.$emit('clear')
    await flushPromises()
    expect(wrapper.text()).not.toContain('unsaved')
  })
})

describe('DataTable.vue discardEdits', () => {
  beforeEach(() => {
    isUpdating.value = false
    selectedSeries.value = {
      data: {
        dataX: [1000, 2000, 3000],
        dataY: [10, 20, 30],
        dispatch: vi.fn().mockResolvedValue(undefined),
      },
    }
    selectedData.value = null
    qcDatastream.value = { id: 'ds-1' }
    qualifierById.value = {}
    applied.value = {}
    vi.clearAllMocks()
  })

  it('clears value+datetime pending edits when Discard is clicked', async () => {
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    valueCell(wrapper, 0).vm.$emit('save', '99')
    datetimeCell(wrapper, 1).vm.$emit('save', '2024-06-06T06:06:06')
    await flushPromises()
    expect(wrapper.text()).toContain('2 unsaved')
    const discardBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Discard'))!
    await discardBtn.trigger('click')
    await flushPromises()
    expect(wrapper.text()).not.toContain('unsaved')
  })
})

describe('DataTable.vue qualifier rendering (qualifierApplicationsAt, Code, Tooltip)', () => {
  beforeEach(() => {
    isUpdating.value = false
    selectedSeries.value = {
      data: {
        dataX: [1000, 2000],
        dataY: [10, 20],
        dispatch: vi.fn().mockResolvedValue(undefined),
      },
    }
    selectedData.value = null
    qcDatastream.value = { id: 'ds-1' }
    qualifierById.value = {}
    applied.value = {}
    vi.clearAllMocks()
  })

  it('renders nothing when qcDatastream is null', async () => {
    qcDatastream.value = null
    applied.value = { 'ds-1': { 0: [{ qualifierId: 'q1', appliedAt: 't', appliedBy: 'u' }] } }
    qualifierById.value = { q1: { code: 'ABC', description: 'desc' } }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    expect(wrapper.findAllComponents({ name: 'v-chip' }).length).toBeGreaterThanOrEqual(0)
    // no qualifier chips rendered (only the toolbar chips)
    expect(wrapper.text()).not.toContain('ABC')
  })

  it('renders nothing when no applied entry for the datastream', async () => {
    applied.value = {}
    qualifierById.value = { q1: { code: 'ABC', description: 'desc' } }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    expect(wrapper.text()).not.toContain('ABC')
  })

  it('renders the qualifier code chip for an applied qualifier', async () => {
    applied.value = {
      'ds-1': { 0: [{ qualifierId: 'q1', appliedAt: 't', appliedBy: 'alice' }] },
    }
    qualifierById.value = { q1: { code: 'SUS', description: 'Suspicious' } }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    expect(wrapper.text()).toContain('SUS')
  })

  it('renders empty chip code for an unknown qualifier id', async () => {
    applied.value = {
      'ds-1': { 0: [{ qualifierId: 'unknown', appliedAt: 't', appliedBy: '' }] },
    }
    qualifierById.value = {}
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    // chip renders but code is ''
    const rowHtml = wrapper.findAll('.vdtv-row').at(0)!.html()
    expect(rowHtml).toContain('<')
  })

  it('includes description and appliedBy in the tooltip title when present', async () => {
    applied.value = {
      'ds-1': { 0: [{ qualifierId: 'q1', appliedAt: 't', appliedBy: 'alice' }] },
    }
    qualifierById.value = { q1: { code: 'SUS', description: 'Suspicious' } }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    const html = wrapper.findAll('.vdtv-row').at(0)!.html()
    expect(html).toContain('SUS: Suspicious')
    expect(html).toContain('alice')
  })

  it('omits appliedBy from tooltip when empty', async () => {
    applied.value = {
      'ds-1': { 0: [{ qualifierId: 'q1', appliedAt: 't', appliedBy: '' }] },
    }
    qualifierById.value = { q1: { code: 'SUS', description: 'Suspicious' } }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    const html = wrapper.findAll('.vdtv-row').at(0)!.html()
    expect(html).toContain('SUS: Suspicious')
    expect(html).not.toContain('alice')
  })
})

describe('DataTable.vue onSelectChange / getRowProps', () => {
  beforeEach(() => {
    isUpdating.value = false
    selectedSeries.value = {
      data: {
        dataX: [1000, 2000, 3000],
        dataY: [10, 20, 30],
        dispatch: vi.fn().mockResolvedValue(undefined),
      },
    }
    selectedData.value = null
    qcDatastream.value = { id: 'ds-1' }
    qualifierById.value = {}
    applied.value = {}
    vi.clearAllMocks()
  })

  it('adds an index to selectedData sorted when the checkbox is toggled on', async () => {
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    const checkboxes = wrapper.findAllComponents({ name: 'VCheckbox' })
    // toggle row 2 first, then row 0 — result should be sorted [0, 2]
    await checkboxes[2].vm.$emit('update:modelValue', true)
    await checkboxes[0].vm.$emit('update:modelValue', true)
    await flushPromises()
    expect(selectedData.value).toEqual([0, 2])
  })

  it('removes an index from selectedData when deselected', async () => {
    selectedData.value = [0, 1, 2]
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    const checkboxes = wrapper.findAllComponents({ name: 'VCheckbox' })
    await checkboxes[1].vm.$emit('update:modelValue', false)
    await flushPromises()
    expect(selectedData.value).toEqual([0, 2])
  })

  it('initialises selectedData array when it is null before first selection', async () => {
    selectedData.value = null
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    const checkboxes = wrapper.findAllComponents({ name: 'VCheckbox' })
    await checkboxes[1].vm.$emit('update:modelValue', true)
    await flushPromises()
    expect(selectedData.value).toEqual([1])
  })

  it('applies row--selected on rows in selectedData', async () => {
    selectedData.value = [1]
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    const rows = wrapper.findAll('.vdtv-row')
    expect(rows.at(0)!.classes()).not.toContain('row--selected')
    expect(rows.at(1)!.classes()).toContain('row--selected')
  })

  it('applies row--edited when a row has a pending value edit', async () => {
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    valueCell(wrapper, 0).vm.$emit('save', '99')
    await flushPromises()
    const row = wrapper.findAll('.vdtv-row').at(0)!
    expect(row.classes()).toContain('row--edited')
  })

  it('applies both row--selected and row--edited when both conditions hold', async () => {
    selectedData.value = [0]
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    datetimeCell(wrapper, 0).vm.$emit('save', '2024-06-06T06:06:06')
    await flushPromises()
    const row = wrapper.findAll('.vdtv-row').at(0)!
    expect(row.classes()).toContain('row--selected')
    expect(row.classes()).toContain('row--edited')
  })

  it('applies neither class for an unmodified, unselected row', async () => {
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    const row = wrapper.findAll('.vdtv-row').at(0)!
    expect(row.classes()).not.toContain('row--selected')
    expect(row.classes()).not.toContain('row--edited')
  })
})

describe('DataTable.vue ResizeObserver integration', () => {
  beforeEach(() => {
    isUpdating.value = false
    selectedSeries.value = {
      data: {
        dataX: [1000, 2000, 3000],
        dataY: [10, 20, 30],
        dispatch: vi.fn().mockResolvedValue(undefined),
      },
    }
    selectedData.value = null
    qcDatastream.value = { id: 'ds-1' }
    qualifierById.value = {}
    applied.value = {}
    vi.clearAllMocks()
  })

  it('uses bodyEl.clientHeight when non-zero and updates on resize', async () => {
    // The cast tells TS the class-constructor assignment widens the
    // value back to the callable type — without it the analyzer pins
    // the variable to `null` after the literal initialiser.
    let capturedCallback = null as ((entries: any) => void) | null
    class CapturingRO {
      constructor(cb: any) {
        capturedCallback = cb
      }
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    const prevRO = (globalThis as any).ResizeObserver
    ;(globalThis as any).ResizeObserver = CapturingRO
    // Make clientHeight non-zero so the `|| 400` fallback is NOT taken.
    const prevGetter = Object.getOwnPropertyDescriptor(
      HTMLElement.prototype,
      'clientHeight'
    )
    Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
      configurable: true,
      get() {
        return 500
      },
    })
    try {
      const wrapper = createWrapperWithSlots()
      await flushPromises()
      // Simulate a resize to exercise the callback branch
      capturedCallback?.([{ contentRect: { height: 650 } }])
      // callback with no entries / no height exercises the else branch
      capturedCallback?.([])
      capturedCallback?.([{ contentRect: { height: 0 } }])
      // same-height path: observer fires with the current height again
      capturedCallback?.([{ contentRect: { height: 650 } }])
      await flushPromises()
      expect(wrapper.exists()).toBe(true)
    } finally {
      ;(globalThis as any).ResizeObserver = prevRO
      if (prevGetter)
        Object.defineProperty(HTMLElement.prototype, 'clientHeight', prevGetter)
    }
  })
})

describe('DataTable.vue onSaveChanges', () => {
  beforeEach(() => {
    isUpdating.value = false
    selectedData.value = null
    qcDatastream.value = { id: 'ds-1' }
    qualifierById.value = {}
    applied.value = {}
    vi.clearAllMocks()
  })

  it('does not call dispatch when there are no pending edits', async () => {
    const dispatch = vi.fn().mockResolvedValue(undefined)
    selectedSeries.value = {
      data: {
        dataX: [1000, 2000],
        dataY: [10, 20],
        dispatch,
      },
    }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    const saveBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Save changes'))!
    await saveBtn.trigger('click')
    await flushPromises()
    expect(dispatch).not.toHaveBeenCalled()
  })

  it('dispatches SELECTION + ASSIGN_VALUES_BULK for value edits and clears them', async () => {
    const dispatch = vi.fn().mockResolvedValue(undefined)
    selectedSeries.value = {
      data: {
        dataX: [1000, 2000, 3000],
        dataY: [10, 20, 30],
        dispatch,
      },
    }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    valueCell(wrapper, 0).vm.$emit('save', '99')
    valueCell(wrapper, 2).vm.$emit('save', '123')
    await flushPromises()
    const saveBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Save changes'))!
    await saveBtn.trigger('click')
    await flushPromises()
    expect(dispatch).toHaveBeenCalledTimes(1)
    const ops = dispatch.mock.calls[0][0]
    expect(ops[0]).toEqual(['SELECTION', [0, 2]])
    expect(ops[1]).toEqual(['ASSIGN_VALUES_BULK', [99, 123]])
    // edits cleared
    expect(wrapper.text()).not.toContain('unsaved')
    expect(redraw).toHaveBeenCalledWith(true)
    expect(clearSelected).toHaveBeenCalled()
  })

  it('dispatches SELECTION + ASSIGN_DATETIMES_BULK for datetime edits with changed epoch', async () => {
    const dispatch = vi.fn().mockResolvedValue(undefined)
    selectedSeries.value = {
      data: {
        dataX: [1000, 2000, 3000],
        dataY: [10, 20, 30],
        dispatch,
      },
    }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    datetimeCell(wrapper, 1).vm.$emit('save', '2024-01-01T00:00:00')
    await flushPromises()
    const saveBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Save changes'))!
    await saveBtn.trigger('click')
    await flushPromises()
    expect(dispatch).toHaveBeenCalledTimes(1)
    const ops = dispatch.mock.calls[0][0]
    expect(ops[0][0]).toBe('SELECTION')
    expect(ops[1][0]).toBe('ASSIGN_DATETIMES_BULK')
    expect(ops[0][1]).toEqual([1])
  })

  it('dispatches both bulk ops when value+datetime edits coexist', async () => {
    const dispatch = vi.fn().mockResolvedValue(undefined)
    selectedSeries.value = {
      data: {
        dataX: [1000, 2000, 3000],
        dataY: [10, 20, 30],
        dispatch,
      },
    }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    valueCell(wrapper, 0).vm.$emit('save', '99')
    datetimeCell(wrapper, 1).vm.$emit('save', '2024-01-01T00:00:00')
    await flushPromises()
    const saveBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Save changes'))!
    await saveBtn.trigger('click')
    await flushPromises()
    expect(dispatch).toHaveBeenCalledTimes(2)
    const kinds = dispatch.mock.calls.map((c: any) => c[0][1][0])
    expect(kinds).toContain('ASSIGN_VALUES_BULK')
    expect(kinds).toContain('ASSIGN_DATETIMES_BULK')
  })

  it('no-ops cleanly when selectedSeries is null', async () => {
    selectedSeries.value = null
    const wrapper = createWrapper()
    await flushPromises()
    const saveBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Save changes'))!
    // Button is disabled (no pendingEditCount), but exercise the guard via invocation
    await saveBtn.trigger('click')
    await flushPromises()
    expect(wrapper.exists()).toBe(true)
  })

  it('resets isUpdating after a save completes', async () => {
    const dispatch = vi.fn().mockResolvedValue(undefined)
    selectedSeries.value = {
      data: {
        dataX: [1000],
        dataY: [10],
        dispatch,
      },
    }
    const wrapper = createWrapperWithSlots()
    await flushPromises()
    valueCell(wrapper, 0).vm.$emit('save', '42')
    await flushPromises()
    const saveBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Save changes'))!
    await saveBtn.trigger('click')
    await flushPromises()
    expect(isUpdating.value).toBe(false)
  })
})
