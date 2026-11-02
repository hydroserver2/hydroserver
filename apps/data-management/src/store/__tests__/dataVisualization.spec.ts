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

  it('filters datastreams by unit name', () => {
    const store = useDataVisStore()
    store.datastreams = [
      { id: 'temperature', unitName: 'Degrees Celsius' },
      { id: 'discharge', unitName: 'Cubic feet per second' },
    ] as any

    store.selectedUnitNames = ['Degrees Celsius']

    expect(store.filteredDatastreams.map((item) => item.id)).toEqual([
      'temperature',
    ])
  })

  it('filters datastreams by method name', () => {
    const store = useDataVisStore()
    store.datastreams = [
      { id: 'temperature', methodName: 'Shielded sensor' },
      { id: 'discharge', methodName: 'Pressure transducer' },
    ] as any

    store.selectedMethodNames = ['Shielded sensor']

    expect(store.filteredDatastreams.map((item) => item.id)).toEqual([
      'temperature',
    ])
  })

  function labelStore() {
    const store = useDataVisStore()
    store.monitoringSites = [
      { id: 'logan', name: 'Logan River' },
      { id: 'bear', name: 'Bear River' },
    ] as any
    store.datastreams = [
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
    return store
  }

  it('includes the site on every trace even for a single plotted site and a single-site table filter', async () => {
    const store = labelStore()
    store.plottedDatastreams = store.datastreams.slice(0, 2)
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
    const store = labelStore()
    store.monitoringSites[1].name = 'Logan River'
    store.plottedDatastreams = [store.datastreams[0], store.datastreams[2]]
    expect(store.plotLabelItems.map((item) => item.label)).toEqual([
      'Discharge\n@ Logan River',
      'Discharge\n@ Logan River',
    ])
  })
})
