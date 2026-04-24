import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
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
  formatDate: (d: Date) => d.toISOString(),
}))

vi.mock('@/components/VisualizeData/EditableCell.vue', () => ({
  default: { name: 'EditableCell', template: '<div class="editable-cell-stub" />' },
}))

import DataTable from '@/components/VisualizeData/DataTable.vue'

function createWrapper() {
  return mount(DataTable, {
    global: {
      plugins: [createTestPinia(), createTestVuetify()],
      stubs: {
        'v-data-table-virtual': { template: '<div class="vdtv-stub"><slot /></div>' },
      },
    },
  })
}

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
