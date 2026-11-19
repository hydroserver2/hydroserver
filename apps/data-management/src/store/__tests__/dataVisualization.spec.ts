import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useDataVisStore } from '../dataVisualization'
import { nextTick } from 'vue'

vi.mock('@/store/observations', () => ({
  useObservationStore: () => ({
    fetchGraphSeries: vi.fn().mockResolvedValue(null),
    fetchGraphSeriesData: vi.fn().mockResolvedValue(null),
  }),
}))

describe('data visualization store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('resolves selected filter names to server filter IDs', () => {
    const store = useDataVisStore()
    store.units = [
      { id: 'celsius', name: 'Degrees Celsius' },
      { id: 'cfs', name: 'Cubic feet per second' },
      { id: 'celsius-2', name: 'Degrees Celsius' },
    ] as any
    store.methods = [
      { id: 'shielded', name: 'Shielded sensor' },
      { id: 'pressure', name: 'Pressure transducer' },
    ] as any
    store.selectedUnitNames = ['Degrees Celsius']
    store.selectedMethodNames = ['Shielded sensor']

    expect(store.datastreamFilters.unitId).toEqual(['celsius', 'celsius-2'])
    expect(store.datastreamFilters.methodId).toEqual(['shielded'])
    expect(store.datastreamFilters.observedPropertyId).toEqual([])
  })

  function labelStore() {
    const store = useDataVisStore()
    store.monitoringSites = [
      { id: 'logan', name: 'Logan River' },
      { id: 'bear', name: 'Bear River' },
    ] as any
    const datastreams = [
      {
        id: 'upstream',
        name: 'Discharge',
        monitoringSiteId: 'logan',
        phenomenonEndTime: '2026-10-01T00:00:00Z',
      },
      {
        id: 'temperature',
        name: 'Temperature',
        monitoringSiteId: 'logan',
        phenomenonEndTime: '2026-10-01T00:00:00Z',
      },
      {
        id: 'downstream',
        name: 'Discharge',
        monitoringSiteId: 'bear',
        phenomenonEndTime: '2026-10-01T00:00:00Z',
      },
    ] as any
    return { store, datastreams }
  }

  it('includes the site on every trace even for a single plotted site and a single-site table filter', async () => {
    const { store, datastreams } = labelStore()
    store.plottedDatastreams = datastreams.slice(0, 2)
    expect(store.plotLabelItems.map((item) => item.label)).toEqual([
      'Discharge\n@ Logan River',
      'Temperature\n@ Logan River',
    ])
    store.selectedMonitoringSites = [store.monitoringSites[0]]
    store.tableSearch = 'Temperature'
    await nextTick()
    expect(store.plotLabelItems.map((item) => item.label)).toEqual([
      'Discharge\n@ Logan River',
      'Temperature\n@ Logan River',
    ])
  })

  it('includes each plotted site when comparing sites, even if their names match', () => {
    const { store, datastreams } = labelStore()
    store.monitoringSites[1].name = 'Logan River'
    store.plottedDatastreams = [datastreams[0], datastreams[2]]
    expect(store.plotLabelItems.map((item) => item.label)).toEqual([
      'Discharge\n@ Logan River',
      'Discharge\n@ Logan River',
    ])
  })
})
