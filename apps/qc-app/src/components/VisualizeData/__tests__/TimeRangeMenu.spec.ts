import { mount } from '@vue/test-utils'
import { reactive, ref } from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'
import { CUSTOM_PRESET_ID, EDITOR_PRESETS } from '@/utils/timeRangePresets'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// jsdom has no visualViewport; Vuetify's overlay positioning reads it.
;(globalThis as any).visualViewport ||= {
  addEventListener() {},
  removeEventListener() {},
  offsetLeft: 0,
  offsetTop: 0,
  width: 1024,
  height: 768,
  scale: 1,
}

const qcDatastream = ref<{ id: string } | null>(null)
const activePresetId = ref(1)
const showSourceContext = ref(true)

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () =>
    reactive({
      qcDatastream,
      activePresetId,
      showSourceContext,
      setShowSourceContext: vi.fn(),
    }),
}))

vi.mock('@/utils/plotting/plotly', () => ({ SOURCE_CONTEXT_COLOR: '#999' }))

vi.mock('@/components/VisualizeData/DataVisTimeFilters.vue', () => ({
  default: {
    name: 'DataVisTimeFilters',
    props: ['presets', 'description'],
    render: () => null,
  },
}))

import TimeRangeMenu from '@/components/VisualizeData/TimeRangeMenu.vue'

function mountIt() {
  return mount(TimeRangeMenu, {
    attachTo: document.body,
    global: { plugins: [createTestPinia(), createTestVuetify()] },
  })
}

async function openMenu(w: ReturnType<typeof mountIt>) {
  await w.find('[data-testid="time-range-btn"]').trigger('click')
  await new Promise((r) => setTimeout(r))
}

describe('TimeRangeMenu.vue', () => {
  beforeEach(() => {
    qcDatastream.value = null
    activePresetId.value = 1
    showSourceContext.value = true
    document.body.innerHTML = ''
  })

  it('labels the Select view range with the active preset', () => {
    activePresetId.value = 5
    const w = mountIt()
    expect(w.find('[data-testid="time-range-btn"]').text()).toContain(
      'Time range · All'
    )
    w.unmount()
  })

  it('labels a manual range as Custom', () => {
    activePresetId.value = CUSTOM_PRESET_ID
    const w = mountIt()
    expect(w.find('[data-testid="time-range-btn"]').text()).toContain('Custom')
    w.unmount()
  })

  it('offers every preset and no context switch in the Select view', async () => {
    const w = mountIt()
    await openMenu(w)
    const filters = w.findComponent({ name: 'DataVisTimeFilters' })
    expect(filters.props('presets')).toBeUndefined()
    expect(document.querySelector('[data-testid="context-toggle"]')).toBeNull()
    w.unmount()
  })

  it('becomes the Context menu while editing', async () => {
    qcDatastream.value = { id: 'qc-1' }
    const w = mountIt()
    expect(w.find('[data-testid="time-range-btn"]').text()).toContain(
      'Context · 1m'
    )
    await openMenu(w)
    const filters = w.findComponent({ name: 'DataVisTimeFilters' })
    expect(filters.props('presets')).toBe(EDITOR_PRESETS)
    expect(
      document.querySelector('[data-testid="context-toggle"]')
    ).not.toBeNull()
    w.unmount()
  })
})
