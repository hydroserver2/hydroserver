import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import DatastreamInformationPanels from '../DatastreamInformationPanels.vue'

const { getItemMock } = vi.hoisted(() => ({
  getItemMock: vi.fn(),
}))

vi.mock('@hydroserver/client', () => ({
  default: {
    datastreams: {
      getItem: getItemMock,
    },
  },
}))

/**
 * `DatastreamInformationPanels.vue` reads `d.workspace.name`, `d.monitoringSite.*`,
 * `d.method.*`, `d.observedProperty.*`, `d.unit.*`, and `d.processingLevel.*` off
 * the object `hs.datastreams.getItem(id, { expand_related: true })` resolves to --
 * this is the merged, `DatastreamExtended`-shaped object `DatastreamService`
 * reconstructs from the backend's `include=` sideload response (chunk 7). This
 * test guards that reconstruction end-to-end through the component, not just the
 * service in isolation.
 */
const mergedDatastream = {
  id: 'ds-1',
  name: 'Stage',
  description: 'Stage datastream',
  valueCount: 12,
  phenomenonBeginTime: null,
  phenomenonEndTime: null,
  observationType: 'OM_Measurement',
  resultType: 'Time Series Coverage',
  sampledMedium: 'Water',
  noDataValue: -9999,
  aggregationStatistic: 'Average',
  intendedTimeSpacing: null,
  intendedTimeSpacingUnit: null,
  timeAggregationInterval: 15,
  timeAggregationIntervalUnit: 'minutes',
  tags: {},
  isPrivate: false,
  isVisible: true,
  workspace: { id: 'ws-1', name: 'Acme Workspace' },
  monitoringSite: {
    id: 'ms-1',
    name: 'Logan River',
    code: 'LR-1',
    description: 'A site',
    type: 'Stream',
    latitude: 41.7,
    longitude: -111.8,
    elevation_m: 1380,
    elevationDatum: 'WGS84',
    adminArea1: 'Utah',
    adminArea2: 'Cache',
    country: 'US',
    isPrivate: false,
  },
  method: {
    id: 'method-1',
    name: 'Sensor Deployment',
    description: 'A method',
    type: 'Instrument Deployment',
    code: 'M-1',
    definition: 'def',
    sensorModelManufacturer: 'Acme Co',
    sensorModel: 'Model X',
    sensorModelDefinition: 'model def',
  },
  observedProperty: {
    id: 'op-1',
    name: 'Stage',
    definition: 'op def',
    description: 'op desc',
    type: 'Hydrology',
    code: 'OP-1',
  },
  processingLevel: {
    id: 'pl-1',
    name: 'Raw',
    code: 'PL-1',
    description: 'pl desc',
    definition: 'pl def',
  },
  unit: {
    id: 'unit-1',
    name: 'Meter',
    symbol: 'm',
    definition: 'unit def',
    type: 'Length',
  },
}

describe('DatastreamInformationPanels', () => {
  it('renders workspace, site, method, observed property, unit, and processing level fields from the merged datastream', async () => {
    getItemMock.mockResolvedValue(mergedDatastream)

    const wrapper = mount(DatastreamInformationPanels, {
      props: { datastreamId: 'ds-1' },
      global: {
        stubs: {
          'v-expansion-panels': { template: '<div><slot /></div>' },
          'v-expansion-panel': { template: '<div><slot /></div>' },
          'v-expansion-panel-text': { template: '<div><slot /></div>' },
          'v-list': { template: '<div><slot /></div>' },
          'v-list-item': { template: '<div><slot /></div>' },
          'v-chip': { template: '<span><slot /></span>' },
        },
      },
    })
    await flushPromises()

    expect(getItemMock).toHaveBeenCalledWith('ds-1', { expand_related: true })

    const text = wrapper.text()
    expect(text).toContain('Acme Workspace')
    expect(text).toContain('Logan River')
    expect(text).toContain('Sensor Deployment')
    expect(text).toContain('Stage')
    expect(text).toContain('Meter')
    expect(text).toContain('Raw')
  })
})
