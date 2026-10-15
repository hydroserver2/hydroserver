import { mount } from '@vue/test-utils'
import {
  defineComponent,
  h,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
} from 'vue'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { createTestVuetify } from '@/utils/test/vuetify'
;(globalThis as any).ResizeObserver ||= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const loadingStates = ref(new Map<string, boolean>())
const seriesDatastreams = ref<any[]>([])
const plotlyOptions = ref<any>({ traces: [] })

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => reactive({ loadingStates, seriesDatastreams }),
}))

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => reactive({ plotlyOptions }),
}))

const lifecycle = vi.hoisted(() => ({ mounts: 0, unmounts: 0 }))

vi.mock('@/components/VisualizeData/Plot.vue', () => ({
  default: defineComponent({
    name: 'PlotStub',
    setup(_props, { slots }) {
      onMounted(() => lifecycle.mounts++)
      onBeforeUnmount(() => lifecycle.unmounts++)
      return () =>
        h('div', { 'data-testid': 'plot-stub' }, [
          h('div', { 'data-testid': 'plot-stub-toolbar' }),
          h('div', { 'data-testid': 'plot-stub-body' }, slots['body-overlay']?.()),
        ])
    },
  }),
}))

vi.mock('@/components/VisualizeData/TimeRangeMenu.vue', () => ({
  default: { name: 'TimeRangeMenu', render: () => null },
}))

import DataVisualization from '@/components/VisualizeData/DataVisualization.vue'

function mountIt() {
  return mount(DataVisualization, {
    global: { plugins: [createTestPinia(), createTestVuetify()] },
  })
}

const setLoading = async (loading: boolean) => {
  loadingStates.value = new Map([['ds-a', loading]])
  await nextTick()
}

describe('DataVisualization.vue', () => {
  beforeEach(() => {
    lifecycle.mounts = 0
    lifecycle.unmounts = 0
    loadingStates.value = new Map()
    seriesDatastreams.value = [{ id: 'ds-a' }]
    plotlyOptions.value = { traces: [{ id: 'ds-a' }] }
  })

  it('keeps the same Plot instance mounted across a data update', async () => {
    const wrapper = mountIt()
    const plot = wrapper.findComponent({ name: 'PlotStub' })
    expect(plot.exists()).toBe(true)

    await setLoading(true)
    expect(
      wrapper.find('[data-testid="data-loading-indicator"]').exists()
    ).toBe(true)
    expect(wrapper.findComponent({ name: 'PlotStub' }).vm).toBe(plot.vm)

    await setLoading(false)
    expect(
      wrapper.find('[data-testid="data-loading-indicator"]').exists()
    ).toBe(false)
    expect(wrapper.findComponent({ name: 'PlotStub' }).vm).toBe(plot.vm)
    expect(lifecycle.mounts).toBe(1)
    expect(lifecycle.unmounts).toBe(0)
  })

  it('mounts the plot under the loading overlay on first load', async () => {
    plotlyOptions.value = { traces: [] }
    const wrapper = mountIt()
    await setLoading(true)
    expect(
      wrapper.find('[data-testid="data-loading-indicator"]').exists()
    ).toBe(true)
    expect(wrapper.findComponent({ name: 'PlotStub' }).exists()).toBe(true)

    plotlyOptions.value = { traces: [{ id: 'ds-a' }] }
    await setLoading(false)
    expect(wrapper.findComponent({ name: 'PlotStub' }).exists()).toBe(true)
    expect(lifecycle.mounts).toBe(1)
  })

  it('puts the loading overlay in the plot body so the toolbar stays usable', async () => {
    const wrapper = mountIt()
    await setLoading(true)
    const body = wrapper.find('[data-testid="plot-stub-body"]')
    expect(body.find('[data-testid="data-loading-indicator"]').exists()).toBe(true)
    expect(
      wrapper.findAll('[data-testid="data-loading-indicator"]')
    ).toHaveLength(1)
  })

  it('counts only the datastreams being fetched, not the edit target', async () => {
    seriesDatastreams.value = [{ id: 'edit' }, { id: 'src' }, { id: 'ds-a' }]
    const wrapper = mountIt()
    loadingStates.value = new Map([
      ['src', true],
      ['ds-a', true],
    ])
    await nextTick()
    expect(
      wrapper.find('[data-testid="data-loading-indicator"]').text()
    ).toContain('Fetching data for 2 datastreams')
  })

  it('shows the no-observations state when the load returns no traces', async () => {
    plotlyOptions.value = { traces: [] }
    const wrapper = mountIt()
    expect(wrapper.text()).toContain('No observations in this range')
    expect(wrapper.findComponent({ name: 'PlotStub' }).exists()).toBe(false)
    expect(wrapper.findComponent({ name: 'TimeRangeMenu' }).exists()).toBe(true)
  })

  it('shows the getting-started steps when nothing is plotted', () => {
    seriesDatastreams.value = []
    plotlyOptions.value = { traces: [] }
    const wrapper = mountIt()
    expect(wrapper.text()).toContain('Find a datastream')
    expect(wrapper.findComponent({ name: 'PlotStub' }).exists()).toBe(false)
    // A window can be set before anything is plotted.
    expect(wrapper.findComponent({ name: 'TimeRangeMenu' }).exists()).toBe(true)
  })
})
