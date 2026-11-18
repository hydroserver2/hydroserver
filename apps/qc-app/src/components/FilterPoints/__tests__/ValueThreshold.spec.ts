import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, vi } from 'vitest'
import { EnumFilterOperations } from '@uwrl/qc-utils'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ isUpdating: ref(false) }),
}))

const dispatchFilter = vi.fn()
vi.mock('@/composables/useFilterDispatch', () => ({
  useFilterDispatch: () => ({
    dispatchFilter,
    getActiveFilterRange: () => undefined,
  }),
}))

import ValueThreshold from '@/components/FilterPoints/ValueThreshold.vue'

describe('ValueThreshold', () => {
  it('Apply runs the applied filters again', async () => {
    const w = mount(ValueThreshold, {
      global: { plugins: [createTestPinia(), createTestVuetify()] },
    })
    const apply = w.find('[data-testid="value-threshold-apply"]')
    expect(apply.attributes('disabled')).toBeDefined()

    await w
      .findAll('button')
      .find((b) => b.text() === 'Add filter')!
      .trigger('click')
    await flushPromises()
    expect(dispatchFilter).toHaveBeenCalledTimes(1)
    expect(apply.attributes('disabled')).toBeUndefined()

    await apply.trigger('click')
    await flushPromises()
    expect(dispatchFilter).toHaveBeenCalledTimes(2)
    expect(dispatchFilter).toHaveBeenLastCalledWith(
      EnumFilterOperations.VALUE_THRESHOLD,
      { filters: [{ operator: 'Greater than', value: 0 }], match: 'any' },
      undefined
    )
  })
})
