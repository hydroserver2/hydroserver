import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const beginDate = ref<string | null>(null)
const endDate = ref<string | null>(null)
const selectedDateBtnId = ref<number | null>(null)
const setDateRange = () => {}
const onDateBtnClick = () => {}

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({
    beginDate,
    endDate,
    selectedDateBtnId,
    setDateRange,
    onDateBtnClick,
  }),
}))

vi.mock('@/components/VisualizeData/DatePickerField.vue', () => ({
  default: {
    name: 'DatePickerField',
    props: ['modelValue', 'placeholder'],
    emits: ['update:modelValue'],
    template: '<div class="date-picker-field-stub" />',
  },
}))

import DataVisTimeFilters from '@/components/VisualizeData/DataVisTimeFilters.vue'

function mountIt(props: Record<string, unknown> = {}) {
  return mount(DataVisTimeFilters, {
    props,
    global: { plugins: [createTestPinia(), createTestVuetify()] },
  })
}

describe('DataVisTimeFilters.vue', () => {
  it('renders the default copy without the prop', () => {
    const w = mountIt()
    expect(w.text()).toContain('Loaded time window')
  })

  it('shows the given description instead of the default', () => {
    const w = mountIt({ description: 'Context around the session.' })
    expect(w.text()).toContain('Context around the session.')
    expect(w.text()).not.toContain('Loaded time window')
  })
})
