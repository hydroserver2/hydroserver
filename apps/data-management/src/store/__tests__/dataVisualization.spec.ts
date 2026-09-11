import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useDataVisStore } from '../dataVisualization'

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
})
