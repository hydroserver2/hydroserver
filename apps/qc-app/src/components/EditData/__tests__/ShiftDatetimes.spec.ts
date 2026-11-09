import { mount, flushPromises } from '@vue/test-utils'
import { ref, shallowRef } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { EnumEditOperations, ObservationRecord, TimeUnit } from '@uwrl/qc-utils'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const QUARTER = 15 * 60 * 1000
const START = Date.UTC(2026, 0, 1)

const selectedData = ref<number[] | null>(null)
const qcDatastream = ref(null)
vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ selectedData, qcDatastream }),
}))

const selectedSeries = shallowRef<{ data: ObservationRecord } | null>(null)
const isUpdating = ref(false)
vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ selectedSeries, isUpdating, redraw: vi.fn() }),
}))

const shiftAmount = ref<number | string>(15)
const selectedShiftUnit = ref('MINUTE')
vi.mock('@/store/userInterface', () => ({
  useUIStore: () => ({
    shiftAmount,
    selectedShiftUnit,
    shiftUnits: ['SECOND', 'MINUTE', 'HOUR', 'DAY', 'WEEK', 'MONTH', 'YEAR'],
  }),
  timeSpacingUnitToTimeUnitKey: () => null,
}))

vi.mock('@/composables/useFilterDispatch', () => ({
  useFilterDispatch: () => ({ recordPostActionSelection: vi.fn() }),
}))

import ShiftDatetimes from '@/components/EditData/ShiftDatetimes.vue'

async function mountPanel() {
  const w = mount(ShiftDatetimes, {
    global: { plugins: [createTestPinia(), createTestVuetify()] },
  })
  await flushPromises()
  return w
}

const shiftButton = (w: Awaited<ReturnType<typeof mountPanel>>) =>
  w.findAll('button').find((b) => b.text() === 'Shift')!

beforeEach(async () => {
  const datetimes = [0, 1, 2, 3, 4].map((i) => START + i * QUARTER)
  const record = new ObservationRecord({ datetimes, dataValues: [1, 2, 3, 4, 5] })
  await record.reload()
  selectedSeries.value = { data: record }
  shiftAmount.value = 15
  selectedShiftUnit.value = 'MINUTE'
})

describe('ShiftDatetimes', () => {
  it('names the taken timestamp instead of shifting onto it', async () => {
    selectedData.value = [1, 2]
    const dispatch = vi.spyOn(selectedSeries.value!.data, 'dispatchAction')
    const w = await mountPanel()

    await shiftButton(w).trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="shift-collision"]').text()).toContain(
      'where one already exists'
    )
    expect(dispatch).not.toHaveBeenCalled()

    // Changing the amount clears the warning.
    shiftAmount.value = 5
    await flushPromises()
    expect(w.find('[data-testid="shift-collision"]').exists()).toBe(false)
  })

  it('shifts when every new timestamp is free', async () => {
    selectedData.value = [2, 3, 4]
    const dispatch = vi.spyOn(selectedSeries.value!.data, 'dispatchAction')
    const w = await mountPanel()

    await shiftButton(w).trigger('click')
    await vi.waitFor(() => expect(dispatch).toHaveBeenCalled())
    expect(dispatch.mock.calls[0].slice(0, 3)).toEqual([
      EnumEditOperations.SHIFT_DATETIMES,
      15,
      TimeUnit.MINUTE,
    ])
    expect(w.find('[data-testid="shift-collision"]').exists()).toBe(false)
  })
})
