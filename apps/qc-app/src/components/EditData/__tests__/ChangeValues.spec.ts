import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { EnumEditOperations, Operator } from '@uwrl/qc-utils'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const operators = Object.keys(Operator)
const selectedOperator = ref(0)
const operationValue = ref<string | number>(0.1)
vi.mock('@/store/userInterface', () => ({
  useUIStore: () => ({ operators, selectedOperator, operationValue }),
}))

const selectedData = ref<number[] | null>([1, 2])
vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ selectedData }),
}))

const dispatchAction = vi.fn()
const isUpdating = ref(false)
vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({
    redraw: vi.fn(),
    selectedSeries: ref({ data: { dispatchAction } }),
    isUpdating,
  }),
}))

vi.mock('@/composables/useFilterDispatch', () => ({
  useFilterDispatch: () => ({ recordPostActionSelection: vi.fn() }),
}))

import ChangeValues from '@/components/EditData/ChangeValues.vue'

const mountPanel = () =>
  mount(ChangeValues, {
    global: { plugins: [createTestPinia(), createTestVuetify()] },
  })

const applyButton = (w: ReturnType<typeof mountPanel>) =>
  w.findAll('button').find((b) => b.text() === 'Apply')!

beforeEach(() => {
  selectedOperator.value = 0
  operationValue.value = 0.1
  dispatchAction.mockClear()
})

describe('ChangeValues input', () => {
  it('asks for a number when the value is empty', async () => {
    selectedOperator.value = operators.indexOf('ASSIGN')
    operationValue.value = ''
    const w = mountPanel()
    await flushPromises()
    expect(w.text()).toContain('Enter a number.')
    expect(applyButton(w).attributes('disabled')).toBeDefined()
  })

  it('does not allow dividing by zero', async () => {
    selectedOperator.value = operators.indexOf('DIV')
    operationValue.value = '0'
    const w = mountPanel()
    await flushPromises()
    expect(w.text()).toContain('Cannot divide by zero.')
    expect(applyButton(w).attributes('disabled')).toBeDefined()
  })

  it('allows zero for the other operators', async () => {
    selectedOperator.value = operators.indexOf('ASSIGN')
    operationValue.value = '0'
    const w = mountPanel()
    await flushPromises()
    expect(applyButton(w).attributes('disabled')).toBeUndefined()
  })

  it('applies a valid value', async () => {
    selectedOperator.value = operators.indexOf('MULT')
    operationValue.value = '2.5'
    const w = mountPanel()
    await flushPromises()
    await applyButton(w).trigger('click')
    await vi.waitFor(() => expect(dispatchAction).toHaveBeenCalled())
    expect(dispatchAction).toHaveBeenCalledWith(
      EnumEditOperations.CHANGE_VALUES,
      Operator.MULT,
      2.5
    )
  })
})
