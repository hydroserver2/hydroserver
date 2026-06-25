import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const thingA = { id: 't-a', name: 'Alpha' }
const thingB = { id: 't-b', name: 'Beta' }
const opX = { id: 'op-x', name: 'Temp' }
const plY = { id: 'pl-y', definition: 'Raw' }

const things = ref<any[]>([thingA, thingB])
const datastreams = ref<any[]>([
  { thing: thingA, observedProperty: opX, processingLevel: plY },
  { thing: thingB, observedProperty: opX, processingLevel: plY },
])
const observedProperties = ref<any[]>([opX])
const processingLevels = ref<any[]>([plY])

const selectedThings = ref<any[]>([])
const selectedObservedPropertyNames = ref<string[]>([])
const selectedProcessingLevelNames = ref<string[]>([])

const matchesSelectedThing = vi.fn(() => true)
const matchesSelectedObservedProperty = vi.fn(() => true)
const matchesSelectedProcessingLevel = vi.fn(() => true)

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({
    things,
    datastreams,
    observedProperties,
    processingLevels,
    selectedThings,
    selectedObservedPropertyNames,
    selectedProcessingLevelNames,
    matchesSelectedThing,
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
    selectedThings.value = []
    selectedObservedPropertyNames.value = []
    selectedProcessingLevelNames.value = []
    things.value = [thingA, thingB]
    datastreams.value = [
      { thing: thingA, observedProperty: opX, processingLevel: plY },
      { thing: thingB, observedProperty: opX, processingLevel: plY },
    ]
    observedProperties.value = [opX]
    processingLevels.value = [plY]
    vi.clearAllMocks()
    matchesSelectedThing.mockReturnValue(true)
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
    selectedThings.value = [thingA]
    selectedObservedPropertyNames.value = ['Temp']
    const wrapper = createWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('2 filters applied')
  })

  it('uses singular "filter" in the applied-count strip for 1 selection', async () => {
    selectedThings.value = [thingA]
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
    selectedThings.value = [thingA, thingB]
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
    selectedThings.value = [thingA]
    selectedObservedPropertyNames.value = ['Temp']
    selectedProcessingLevelNames.value = ['Raw']
    const wrapper = createWrapper()
    await flushPromises()
    const clearBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Clear'))
    expect(clearBtn).toBeTruthy()
    await clearBtn!.trigger('click')
    expect(selectedThings.value).toEqual([])
    expect(selectedObservedPropertyNames.value).toEqual([])
    expect(selectedProcessingLevelNames.value).toEqual([])
  })

  it('removes stale selections when the sorted list shrinks', async () => {
    selectedThings.value = [thingA, thingB]
    const wrapper = createWrapper()
    await flushPromises()

    things.value = [thingA]
    datastreams.value = [
      { thing: thingA, observedProperty: opX, processingLevel: plY },
    ]
    await flushPromises()
    expect(selectedThings.value).toEqual([thingA])
    wrapper.unmount()
  })
})
