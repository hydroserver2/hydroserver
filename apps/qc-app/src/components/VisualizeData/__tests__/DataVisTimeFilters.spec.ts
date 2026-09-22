import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { describe, it, expect, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'

const beginDate = ref<string | null>(null)
const endDate = ref<string | null>(null)
const activePresetId = ref<number | null>(null)
const setDateRange = () => {}
const onDateBtnClick = () => {}

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({
    beginDate,
    endDate,
    activePresetId,
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
import { EDITOR_PRESETS } from '@/utils/timeRangePresets'

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

  it('offers every preset, YTD included, by default', () => {
    const w = mountIt()
    expect(w.find('[data-testid="date-preset-YTD"]').exists()).toBe(true)
    expect(w.find('[data-testid="date-preset-All"]').exists()).toBe(true)
  })

  it('can hide YTD with the editor presets', () => {
    const w = mountIt({ presets: EDITOR_PRESETS })
    expect(w.find('[data-testid="date-preset-YTD"]').exists()).toBe(false)
    expect(w.find('[data-testid="date-preset-1w"]').exists()).toBe(true)
    expect(w.find('[data-testid="date-preset-All"]').exists()).toBe(true)
  })

  it('highlights All for a saved YTD preference with the editor presets, keeping the preference', () => {
    activePresetId.value = 3
    const w = mountIt({ presets: EDITOR_PRESETS })
    expect(w.find('[data-testid="date-preset-All"]').classes()).toContain('v-chip--variant-tonal')
    expect(w.find('[data-testid="date-preset-1w"]').classes()).toContain('v-chip--variant-outlined')
    expect(activePresetId.value).toBe(3)
  })

  it('highlights YTD itself where it is offered', () => {
    activePresetId.value = 3
    const w = mountIt()
    expect(w.find('[data-testid="date-preset-YTD"]').classes()).toContain('v-chip--variant-tonal')
    expect(w.find('[data-testid="date-preset-All"]').classes()).toContain('v-chip--variant-outlined')
  })
})
