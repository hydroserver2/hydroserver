import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const filteredDatastreams = ref<any[]>([])
const plottedDatastreams = ref<any[]>([])
const qcDatastream = ref<any>(null)

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({
    filteredDatastreams,
    plottedDatastreams,
    qcDatastream,
    toggleDatastream: vi.fn(),
    clearPlottedDatastreams: vi.fn(),
  }),
}))

vi.mock('@/utils/csvExport', () => ({
  downloadDatastreamsCsvZip: vi.fn(),
}))

import DataVisDatasetsTable from '@/components/VisualizeData/DataVisDatasetsTable.vue'

const virtualTableStub = {
  name: 'VDataTableVirtualStub',
  props: ['items'],
  template: `
    <div class="virtual-table-stub">
      <div v-for="item in items" :key="item.id" class="table-item">
        {{ item.id }}
      </div>
      <slot name="no-data" v-if="!items.length" />
    </div>
  `,
}

function mountTable() {
  return mount(DataVisDatasetsTable, {
    global: {
      plugins: [createTestPinia(), createTestVuetify()],
      stubs: {
        'v-data-table-virtual': virtualTableStub,
        DatastreamInformationCard: true,
      },
    },
  })
}

describe('DataVisDatasetsTable search', () => {
  beforeEach(() => {
    plottedDatastreams.value = []
    qcDatastream.value = null
    filteredDatastreams.value = [
      {
        id: 'available-temperature',
        monitoringSite: { code: 'UPPR', name: 'Upper Creek' },
        observedProperty: { name: 'Temperature' },
        processingLevel: { definition: 'Raw' },
      },
      {
        id: 'available-flow',
        monitoringSite: { code: 'LOWR', name: 'Lower Creek' },
        observedProperty: { name: 'Flow' },
        processingLevel: { definition: 'QC' },
      },
    ]
  })

  it('searches only the rows remaining after the other filters', async () => {
    const wrapper = mountTable()
    const input = wrapper.get('input')

    await input.setValue('temperature')

    expect(wrapper.findAll('.table-item').map((row) => row.text())).toEqual([
      'available-temperature',
    ])
  })
})
