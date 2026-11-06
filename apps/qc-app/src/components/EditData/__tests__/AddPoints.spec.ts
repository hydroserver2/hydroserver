import { mount, flushPromises } from '@vue/test-utils'
import { ref, shallowRef } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { EnumEditOperations, ObservationRecord } from '@uwrl/qc-utils'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const QUARTER = 15 * 60 * 1000
const START = Date.UTC(2026, 0, 1)

const selectedData = ref<number[] | null>(null)
vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ selectedData }),
}))

const selectedSeries = shallowRef<{ data: ObservationRecord } | null>(null)
const isUpdating = ref(false)
vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ selectedSeries, isUpdating, redraw: vi.fn() }),
}))

vi.mock('@/store/userInterface', () => ({
  useUIStore: () => ({ noDataValue: ref(-9999) }),
}))

vi.mock('@/utils/plotting/plotly', () => ({ intendedSpacingMs: () => null }))

vi.mock('@/composables/useFilterDispatch', () => ({
  useFilterDispatch: () => ({ recordPostActionSelection: vi.fn() }),
}))

import AddPoints from '@/components/EditData/AddPoints.vue'

async function mountPanel() {
  const w = mount(AddPoints, {
    global: {
      plugins: [createTestPinia(), createTestVuetify()],
      stubs: { DatePickerField: true },
    },
  })
  await flushPromises()
  return w
}

const addButton = (w: Awaited<ReturnType<typeof mountPanel>>) =>
  w.findAll('button').find((b) => b.text().startsWith('Add '))!

beforeEach(async () => {
  const datetimes = [0, 1, 2, 3].map((i) => START + i * QUARTER)
  const record = new ObservationRecord({ datetimes, dataValues: [1, 2, 3, 4] })
  await record.reload()
  selectedSeries.value = { data: record }
  selectedData.value = null
})

describe('AddPoints', () => {
  it('proposes a free time after the last point when there is no intended spacing', async () => {
    const dispatch = vi.spyOn(selectedSeries.value!.data, 'dispatchAction')
    const w = await mountPanel()
    expect(w.find('[data-testid="add-points-collision"]').exists()).toBe(false)

    await addButton(w).trigger('click')
    await vi.waitFor(() => expect(dispatch).toHaveBeenCalled())
    expect(dispatch).toHaveBeenCalledWith(EnumEditOperations.ADD_POINTS, [
      [START + 4 * QUARTER, -9999],
    ])
  })

  it('names a taken timestamp and blocks adding it', async () => {
    const record = selectedSeries.value!.data
    vi.spyOn(record, 'findTimeCollision').mockReturnValue(START + QUARTER)
    const dispatch = vi.spyOn(record, 'dispatchAction')
    const w = await mountPanel()

    expect(w.find('[data-testid="add-points-collision"]').text()).toContain(
      'A point already exists at'
    )
    expect(addButton(w).attributes('disabled')).toBeDefined()
    await addButton(w).trigger('click')
    expect(dispatch).not.toHaveBeenCalled()
  })
})
