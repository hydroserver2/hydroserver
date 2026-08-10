import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const monitoringSiteA = { id: 't-a', name: 'Alpha' }
const monitoringSiteB = { id: 't-b', name: 'Beta' }
const opX = { id: 'op-x', name: 'Temp' }
const plY = { id: 'pl-y', definition: 'Raw' }

const monitoringSites = ref<any[]>([monitoringSiteA, monitoringSiteB])
const datastreams = ref<any[]>([
  { monitoringSite: monitoringSiteA, observedProperty: opX, processingLevel: plY },
  { monitoringSite: monitoringSiteB, observedProperty: opX, processingLevel: plY },
])
const observedProperties = ref<any[]>([opX])
const processingLevels = ref<any[]>([plY])

const selectedMonitoringSites = ref<any[]>([])
const selectedObservedPropertyNames = ref<string[]>([])
const selectedProcessingLevelNames = ref<string[]>([])

const matchesSelectedMonitoringSite = vi.fn(() => true)
const matchesSelectedObservedProperty = vi.fn(() => true)
const matchesSelectedProcessingLevel = vi.fn(() => true)

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({
    monitoringSites,
    datastreams,
    observedProperties,
    processingLevels,
    selectedMonitoringSites,
    selectedObservedPropertyNames,
    selectedProcessingLevelNames,
    matchesSelectedMonitoringSite,
    matchesSelectedObservedProperty,
    matchesSelectedProcessingLevel,
  }),
}))

vi.mock('@/components/VisualizeData/FilterPanel.vue', () => ({
  default: {
    name: 'FilterPanel',
    props: ['icon', 'label', 'total', 'selectedCount', 'search'],
    emits: ['update:search'],
    template:
      '<div class="filter-panel-stub" :data-label="label" :data-total="total" :data-selected="selectedCount"><slot /></div>',
  },
}))

import DatastreamFilters from '@/components/VisualizeData/DatastreamFilters.vue'

function createWrapper() {
  return mount(DatastreamFilters, {
    global: {
      plugins: [createTestPinia(), createTestVuetify()],
      stubs: {
        'v-virtual-scroll': {
          props: ['items'],
          template:
            '<div><template v-for="(item, i) in items" :key="i"><slot :item="item" /></template></div>',
        },
      },
    },
  })
}

describe('DatastreamFilters.vue', () => {
  beforeEach(() => {
    selectedMonitoringSites.value = []
    selectedObservedPropertyNames.value = []
    selectedProcessingLevelNames.value = []
    monitoringSites.value = [monitoringSiteA, monitoringSiteB]
    datastreams.value = [
      { monitoringSite: monitoringSiteA, observedProperty: opX, processingLevel: plY },
      { monitoringSite: monitoringSiteB, observedProperty: opX, processingLevel: plY },
    ]
    observedProperties.value = [opX]
    processingLevels.value = [plY]
    vi.clearAllMocks()
    matchesSelectedMonitoringSite.mockReturnValue(true)
    matchesSelectedObservedProperty.mockReturnValue(true)
    matchesSelectedProcessingLevel.mockReturnValue(true)
  })

  it('does not render the applied-count strip when no filters are selected', async () => {
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.text()).not.toMatch(/\d+ filters? applied/)
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('shows the applied-count strip with the total number of selections', async () => {
    selectedMonitoringSites.value = [monitoringSiteA]
    selectedObservedPropertyNames.value = ['Temp']
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('2 filters applied')
  })

  it('uses singular "filter" in the applied-count strip for 1 selection', async () => {
    selectedMonitoringSites.value = [monitoringSiteA]
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('1 filter applied')
  })

  it('passes the correct total counts to each FilterPanel', async () => {
    const wrapper = createWrapper()
    await flushPromises()
    const panels = wrapper.findAll('.filter-panel-stub')
    expect(panels.length).toBe(3)
    expect(panels[0].attributes('data-label')).toBe('Sites')
    expect(panels[0].attributes('data-total')).toBe('2')
    expect(panels[1].attributes('data-label')).toBe('Observed properties')
    expect(panels[1].attributes('data-total')).toBe('1')
    expect(panels[2].attributes('data-label')).toBe('Processing levels')
    expect(panels[2].attributes('data-total')).toBe('1')
  })

  it('reflects selected counts in each FilterPanel', async () => {
    selectedMonitoringSites.value = [monitoringSiteA, monitoringSiteB]
    selectedObservedPropertyNames.value = ['Temp']
    selectedProcessingLevelNames.value = []
    const wrapper = createWrapper()
    await flushPromises()
    const panels = wrapper.findAll('.filter-panel-stub')
    expect(panels[0].attributes('data-selected')).toBe('2')
    expect(panels[1].attributes('data-selected')).toBe('1')
    expect(panels[2].attributes('data-selected')).toBe('0')
  })

  it('clicking Clear resets all filter selections', async () => {
    selectedMonitoringSites.value = [monitoringSiteA]
    selectedObservedPropertyNames.value = ['Temp']
    selectedProcessingLevelNames.value = ['Raw']
    const wrapper = createWrapper()
    await flushPromises()
    const clearBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Clear'))
    expect(clearBtn).toBeTruthy()
    await clearBtn!.trigger('click')
    expect(selectedMonitoringSites.value).toEqual([])
    expect(selectedObservedPropertyNames.value).toEqual([])
    expect(selectedProcessingLevelNames.value).toEqual([])
  })

  it('removes stale selections when the sorted list shrinks', async () => {
    selectedMonitoringSites.value = [monitoringSiteA, monitoringSiteB]
    const wrapper = createWrapper()
    await flushPromises()

    monitoringSites.value = [monitoringSiteA]
    datastreams.value = [
      { monitoringSite: monitoringSiteA, observedProperty: opX, processingLevel: plY },
    ]
    await flushPromises()
    expect(selectedMonitoringSites.value).toEqual([monitoringSiteA])
    wrapper.unmount()
  })
})
